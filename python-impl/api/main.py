"""
FastAPI入口 — 提供REST API + SSE流式响应
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.supervisor import create_supervisor_graph
from agents.ticket_handler import TicketStore
from memory.working_memory import WorkingMemory
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from mcp.mcp_server import MCPToolServer
from mcp.backend_client import BackendClient
from mcp.backend_tools import create_backend_tools
from mcp.user_backend_tools import create_user_backend_tools
from tracing.otel_config import init_tracer, AgentMetrics

load_dotenv()


working_memory = WorkingMemory()
short_term_memory = ShortTermMemory(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
long_term_memory = LongTermMemory(index_path=os.getenv("FAISS_INDEX_PATH", "./vector_store/faiss_index"))

# 注册管理员端工具（token header）和用户端工具（authentication header）
mcp_server = create_backend_tools(MCPToolServer(), BackendClient())
mcp_server = create_user_backend_tools(mcp_server, BackendClient(header_name="authentication"))
metrics = AgentMetrics()
ticket_store = TicketStore()
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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    token_hdr: str | None = Header(None, alias="token"),
    auth_hdr: str | None = Header(None, alias="authentication"),
):
    """主聊天接口"""
    if graph is None:
        raise HTTPException(status_code=503, detail="系统初始化中")

    session_id = request.session_id or str(uuid.uuid4())

    # 优先 token header（管理员），其次 authentication header（用户），最后 body
    if token_hdr:
        auth_token = token_hdr
        auth_type = "admin"
    elif auth_hdr:
        auth_token = auth_hdr
        auth_type = "user"
    else:
        auth_token = request.token
        auth_type = "admin"  # body token 默认视为管理员

    await short_term_memory.add_message(session_id, "user", request.message)

    from langchain_core.messages import HumanMessage

    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": request.user_id,
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
    )


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """获取对话历史"""
    history = await short_term_memory.get_history(session_id)
    return {"session_id": session_id, "messages": history}


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
