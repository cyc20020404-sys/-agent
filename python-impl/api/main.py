"""
FastAPI入口 — 提供REST API + SSE流式响应
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.supervisor import create_supervisor_graph
from agents.ticket_handler import TicketStore
from agents.human_handoff import HumanHandoffStore
from agents.ws_manager import ws_manager
from memory.working_memory import WorkingMemory
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.mysql_store import MysqlStore
from mcp.mcp_server import MCPToolServer
from mcp.backend_client import BackendClient
from mcp.backend_tools import create_backend_tools
from mcp.user_backend_tools import create_user_backend_tools
from tracing.otel_config import init_tracer, AgentMetrics

load_dotenv()


working_memory = WorkingMemory()

# 配置 MySQL 持久化存储（可选，未配置则仅用 Redis）
_mysql_host = os.getenv("MYSQL_HOST")
_mysql_db = os.getenv("MYSQL_DATABASE")
_mysql_user = os.getenv("MYSQL_USER")
if _mysql_host and _mysql_db and _mysql_user:
    chat_history_store = MysqlStore(
        host=_mysql_host,
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=_mysql_db,
        user=_mysql_user,
        password=os.getenv("MYSQL_PASSWORD", ""),
        pool_size=int(os.getenv("MYSQL_POOL_SIZE", "5")),
    )
else:
    chat_history_store = None

short_term_memory = ShortTermMemory(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    mysql_store=chat_history_store,
)
long_term_memory = LongTermMemory(index_path=os.getenv("FAISS_INDEX_PATH", "./vector_store/faiss_index"))

# 注册管理员端工具（token header）和用户端工具（authentication header）
mcp_server = create_backend_tools(MCPToolServer(), BackendClient())
mcp_server = create_user_backend_tools(mcp_server, BackendClient(base_url="http://localhost:8080/user", header_name="authentication"))
metrics = AgentMetrics()
ticket_store = TicketStore()
handoff_store = HumanHandoffStore()
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global graph

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_endpoint = otlp_endpoint.strip() or None

    init_tracer(
        service_name=os.getenv("OTEL_SERVICE_NAME", "smart-cs-multi-agent"),
        otlp_endpoint=otlp_endpoint,
    )

    graph = create_supervisor_graph(
        working_memory=working_memory,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        ticket_store=ticket_store,
        mcp_server=mcp_server,
        handoff_store=handoff_store,
    )

    # 外卖FAQ知识库
    long_term_memory.add_document(
        content="菜品分类：本店提供火锅配菜、海鲜料理、烧烤系列、蜀味烤鱼、蜀味牛蛙、水煮鱼、湘菜系列、粤式点心、特色蒸菜、传统主食、新鲜时蔬、甜品小吃、汤类、酒水饮料等分类。每类有丰富的菜品可供选择。",
        source="menu_categories.md",
    )
    long_term_memory.add_document(
        content="退款政策：用户在订单未接单前可随时取消订单。已接单未配送的订单可联系客服取消，已配送的订单如遇质量问题可在收到后2小时内申请退款。退款将在3-5个工作日内原路退回。",
        source="refund_policy.md",
    )
    long_term_memory.add_document(
        content="下单流程：1.浏览菜品或套餐 2.加入购物车 3.选择收货地址 4.选择支付方式（微信支付）5.确认下单 6.等待商家接单 7.配送中 8.确认收货。配送费¥5.20，店铺地址位于江西上饶，店铺名称为苍穹食堂。",
        source="ordering_guide.md",
    )
    long_term_memory.add_document(
        content="店铺营业信息：苍穹食堂是一家10年老店，专注为顾客打造专业的大众化美食外送餐饮。提供火锅、烤鱼、牛蛙、海鲜、湘菜等多种美食。支持微信小程序下单，配送范围覆盖周边区域。",
        source="shop_info.md",
    )

    yield

    # 关闭 MySQL 连接池
    if chat_history_store is not None:
        await chat_history_store.close()


app = FastAPI(
    title="智能客服多Agent系统",
    description="基于LangGraph的Supervisor编排多Agent智能客服系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: str | None = None
    token: str | None = None  # 管理员JWT令牌，透传给后端API


class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: str
    compliance_passed: bool
    escalated: bool = False


class TicketDetailResponse(BaseModel):
    ticket_id: str
    type: str
    priority: str
    status: str
    summary: str
    details: str
    user_id: str
    assigned_queue: str
    current_stage: str
    handoff_mode: str
    last_event: str
    created_at: str
    updated_at: str


def _parse_auth(token_hdr, auth_hdr, body_token):
    """统一鉴权解析"""
    if token_hdr:
        return token_hdr, "admin"
    elif auth_hdr:
        return auth_hdr, "user"
    else:
        return body_token or "", "admin"


def _build_initial_state(message, user_id, session_id, auth_token, auth_type):
    """构建 Graph 初始状态"""
    from langchain_core.messages import HumanMessage
    return {
        "messages": [HumanMessage(content=message)],
        "user_id": user_id,
        "session_id": session_id,
        "intent": "",
        "sub_results": {},
        "compliance_passed": True,
        "final_response": "",
        "current_agent": "",
        "retry_count": 0,
        "auth_token": auth_token or "",
        "auth_type": auth_type,
    }


# ── SSE 辅助 ────────────────────────────────────────────────

def _sse(data: dict) -> str:
    """将一个 dict 格式化为 SSE data 行"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _run_graph_with_events(initial_state: dict, config: dict, queue: asyncio.Queue):
    """
    运行 LangGraph 并在关键节点推送事件到 queue。
    利用 graph.astream_events() (LangGraph >= 0.2) 捕获每个节点完成事件。
    """
    if graph is None:
        await queue.put({"type": "error", "text": "系统未初始化"})
        await queue.put({"type": "done"})
        return

    try:
        # 先用手动模式：逐步执行 nodes，每步推事件
        # LangGraph 的 astream 在 subgraph 内部可能不支持 v1 事件，
        # 所以采用手动推进 + 状态快照
        await queue.put({"type": "status", "text": "正在分析您的问题..."})

        # 方法：直接调用 ainvoke, 但在前后推事件
        # 因为没有 graph.astream_events 的可靠支持，
        # 我们用 asyncio.create_task 在后台跑，同时先推状态
        result = await graph.ainvoke(initial_state, config=config)

        intent = result.get("intent", "unknown")
        compliance = result.get("compliance_passed", True)
        final = result.get("final_response", "系统处理异常，请稍后重试")

        await queue.put({
            "type": "meta",
            "intent": intent,
            "compliance_passed": compliance,
            "escalated": intent == "human_handoff",
        })
        await queue.put({"type": "content", "text": final})
        await queue.put({"type": "done"})

    except Exception as e:
        await queue.put({"type": "error", "text": f"处理失败: {str(e)}"})
        await queue.put({"type": "done"})


# ── API Routes ──────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    token_hdr: str | None = Header(None, alias="token"),
    auth_hdr: str | None = Header(None, alias="authentication"),
):
    """主聊天接口（非流式，兼容旧版）"""
    if graph is None:
        raise HTTPException(status_code=503, detail="系统初始化中")

    session_id = request.session_id or str(uuid.uuid4())
    auth_token, auth_type = _parse_auth(token_hdr, auth_hdr, request.token)

    await short_term_memory.add_message(session_id, "user", request.message)

    # Check if session is already escalated to human agent
    if handoff_store.is_escalated(session_id):
        escalated_session = handoff_store.get(session_id)
        if escalated_session and escalated_session.status == "active":
            handoff_store.user_message(session_id, request.message)

        return ChatResponse(
            response=".",
            session_id=session_id,
            intent="human_handoff",
            compliance_passed=True,
            escalated=True,
        )

    initial_state = _build_initial_state(request.message, request.user_id, session_id, auth_token, auth_type)
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

    final_response = result.get("final_response", "系统处理异常，请稍后重试")
    await short_term_memory.add_message(session_id, "assistant", final_response)

    return ChatResponse(
        response=final_response,
        session_id=session_id,
        intent=result.get("intent", "unknown"),
        compliance_passed=result.get("compliance_passed", True),
        escalated=result.get("intent") == "human_handoff",
    )


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    token_hdr: str | None = Header(None, alias="token"),
    auth_hdr: str | None = Header(None, alias="authentication"),
):
    """SSE 流式聊天接口"""
    if graph is None:
        raise HTTPException(status_code=503, detail="系统初始化中")

    session_id = request.session_id or str(uuid.uuid4())
    auth_token, auth_type = _parse_auth(token_hdr, auth_hdr, request.token)

    await short_term_memory.add_message(session_id, "user", request.message)

    # If already escalated to human agent, bypass the AI graph
    # Agent replies are delivered by H5 polling — not duplicated here.
    if handoff_store.is_escalated(session_id):
        escalated_session = handoff_store.get(session_id)
        if escalated_session and escalated_session.status == "active":
            handoff_store.user_message(session_id, request.message)

        response_text = "."

        async def escalated_event_generator() -> AsyncGenerator[str, None]:
            yield _sse({"type": "status", "text": "人工客服"})
            yield _sse({"type": "meta", "intent": "human_handoff", "compliance_passed": True, "escalated": True})
            yield _sse({"type": "content", "text": response_text})
            yield _sse({"type": "done"})

        return StreamingResponse(
            escalated_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    initial_state = _build_initial_state(request.message, request.user_id, session_id, auth_token, auth_type)
    config = {"configurable": {"thread_id": session_id}}

    queue: asyncio.Queue = asyncio.Queue()

    async def event_generator() -> AsyncGenerator[str, None]:
        # 后台任务：运行 graph
        task = asyncio.create_task(_run_graph_with_events(initial_state, config, queue))

        full_text = ""
        try:
            while True:
                event = await queue.get()
                event_type = event.get("type", "")

                if event_type == "done":
                    break

                if event_type == "error":
                    full_text = event.get("text", "")
                    yield _sse(event)
                    break

                if event_type == "content":
                    text = event.get("text", "")
                    full_text += text

                yield _sse(event)
        finally:
            await task
            # 保存完整回复到短期记忆
            if full_text:
                await short_term_memory.add_message(session_id, "assistant", full_text)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """获取对话历史——包含当前 escalation 状态"""
    history = await short_term_memory.get_history(session_id)
    escalated = handoff_store.is_escalated(session_id)  # resolved 的会话返回 False
    return {
        "session_id": session_id,
        "messages": history,
        "escalated": escalated,
    }


@app.get("/api/tools")
async def list_tools():
    """MCP工具发现接口"""
    return {"tools": mcp_server.list_tools()}


@app.post("/api/tools/call")
async def call_tool(request: dict):
    """MCP工具调用接口"""
    result = await mcp_server.call_tool(
        name=request.get("name", ""),
        arguments=request.get("arguments", {}),
    )
    return {
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@app.get("/api/metrics")
async def get_metrics():
    """获取系统指标"""
    return {
        "agent_metrics": metrics.get_summary(),
        "tool_call_log": mcp_server.get_call_log(last_n=20),
    }


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(ticket_id: str):
    """获取结构化工单详情"""
    ticket = ticket_store.query(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"未找到工单号 {ticket_id}")
    return TicketDetailResponse(**ticket)


# ── 人工客服队列 API ──────────────────────────────────────

class HandoffSessionItem(BaseModel):
    session_id: str
    user_id: str
    status: str
    message_count: int
    agent_id: str
    agent_name: str
    created_at: str
    accepted_at: str
    resolved_at: str


class HandoffMessageItem(BaseModel):
    role: str
    content: str
    timestamp: str


class AcceptRequest(BaseModel):
    agent_id: str = "admin"
    agent_name: str = "管理员"


class ReplyRequest(BaseModel):
    message: str


@app.get("/api/human-queue", response_model=list[HandoffSessionItem])
async def list_human_queue():
    """获取所有升级到人工的会话列表"""
    return handoff_store.list_queued()


@app.post("/api/human-queue/{session_id}/accept", response_model=HandoffSessionItem)
async def accept_human_session(session_id: str, req: AcceptRequest = AcceptRequest()):
    """管理员接管人工会话"""
    session = handoff_store.accept(session_id, req.agent_id, req.agent_name)
    if not session:
        raise HTTPException(status_code=404, detail=f"未找到会话 {session_id}")
    return session.to_dict()


@app.post("/api/human-queue/{session_id}/reply")
async def agent_reply(session_id: str, req: ReplyRequest):
    """管理员发送人工回复"""
    session = handoff_store.agent_reply(session_id, req.message)
    if not session:
        raise HTTPException(status_code=404, detail=f"未找到会话 {session_id}")
    return {"success": True, "session_id": session_id}


@app.get("/api/human-queue/{session_id}/messages", response_model=list[HandoffMessageItem])
async def get_human_session_messages(session_id: str, since: int = 0):
    """获取人工会话的消息（管理员端轮询）—— 包含接管前的聊天记录"""
    session = handoff_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"未找到会话 {session_id}")

    # 1. 获取接管前的聊天记录 (short_term_memory 中存储了全部 user + assistant 消息)
    history = await short_term_memory.get_history(session_id)

    # 2. 与 handoff_store 中的消息合并，按 (role, content) 去重
    existing = set()
    all_msgs: list[dict] = []

    for msg in history:
        key = (msg.get("role", ""), msg.get("content", ""))
        existing.add(key)
        all_msgs.append(msg)

    for msg in session.messages:
        key = (msg.get("role", ""), msg.get("content", ""))
        if key not in existing:
            all_msgs.append(msg)

    return all_msgs[since:]


@app.post("/api/human-queue/{session_id}/user-message")
async def user_message_to_agent(session_id: str, req: ReplyRequest):
    """用户端发消息给人工客服（已升级会话中用户继续发消息）"""
    session = handoff_store.user_message(session_id, req.message)
    if not session:
        raise HTTPException(status_code=404, detail=f"未找到会话 {session_id}")
    return {"success": True, "session_id": session_id}


@app.get("/api/human-queue/{session_id}/user-poll")
async def user_poll_agent(session_id: str, since: int = 0):
    """用户端轮询人工回复"""
    session = handoff_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"未找到会话 {session_id}")
    # Only return agent replies
    agent_messages = [m for m in session.messages[since:] if m.get("role") == "agent"]
    return {"status": session.status, "messages": agent_messages}


# ── WebSocket 实时消息通道 ────────────────────────────────

@app.websocket("/ws/user/{session_id}")
async def ws_user(session_id: str, ws: WebSocket):
    """H5 用户端 WebSocket — 接收人工回复"""
    await ws_manager.connect_user(session_id, ws)
    try:
        while True:
            text = await ws.receive_text()
            data = json.loads(text)
            msg_type = data.get("type", "")
            if msg_type == "user_message":
                session = handoff_store.get(session_id)
                # 会话已解决或不存在 → 通知H5切回AI模式
                if session is None or session.status == "resolved":
                    await short_term_memory.add_message(session_id, "user", data.get("content", ""))
                    await ws_manager._send_to_user(session_id, {
                        "type": "session_resolved",
                        "session_id": session_id,
                    })
                else:
                    handoff_store.user_message(session_id, data.get("content", ""))
                    await short_term_memory.add_message(session_id, "user", data.get("content", ""))
                    await ws_manager.user_to_admin(session_id, data.get("content", ""))
            elif msg_type == "pong":
                pass
    except (WebSocketDisconnect, Exception):
        ws_manager.disconnect_user(session_id)


@app.websocket("/ws/admin/{session_id}")
async def ws_admin(session_id: str, ws: WebSocket):
    """管理后台 WebSocket — 接收用户消息 + 发送人工回复"""
    if not handoff_store.get(session_id):
        if handoff_store.is_escalated(session_id):
            handoff_store.accept(session_id)
        else:
            await ws.accept()
            await ws.send_text(json.dumps({"type": "error", "text": "会话不存在"}))
            await ws.close()
            return

    await ws_manager.connect_admin(session_id, ws)
    try:
        while True:
            text = await ws.receive_text()
            data = json.loads(text)
            msg_type = data.get("type", "")
            if msg_type == "agent_message":
                content = data.get("content", "")
                agent_name = data.get("agent_name", "")
                handoff_store.agent_reply(session_id, content)
                await short_term_memory.add_message(session_id, "assistant", f"[人工客服] {content}")
                await ws_manager.admin_to_user(session_id, content, agent_name)
            elif msg_type == "accept":
                handoff_store.accept(
                    session_id,
                    data.get("agent_id", "admin"),
                    data.get("agent_name", "管理员"),
                )
                await ws.send_text(json.dumps({"type": "accepted", "session_id": session_id}))
            elif msg_type == "resolve":
                handoff_store.resolve(session_id)
                await ws_manager.admin_to_user(session_id, "感谢您的咨询，本次服务已结束，如有其他问题欢迎再次联系我们。", "系统")
                # 通知H5会话已结束，让H5切回AI模式
                await ws_manager._send_to_user(session_id, {"type": "resolved", "session_id": session_id})
                await ws_manager._send_to_admin(session_id, {"type": "resolved", "session_id": session_id})
            elif msg_type == "pong":
                pass
    except (WebSocketDisconnect, Exception):
        ws_manager.disconnect_admin(session_id)

    # Clean up if no one is connected
    if not ws_manager._sessions.get(session_id):
        pass
    elif not ws_manager._sessions[session_id].user_ws and not ws_manager._sessions[session_id].admin_ws:
        ws_manager._sessions.pop(session_id, None)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )