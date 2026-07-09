"""
Supervisor编排Agent — 中央协调者
负责接收用户请求，根据意图路由到对应子Agent，汇总结果返回。
采用LangGraph StateGraph实现，支持并行调度和Human-in-the-Loop断点。
"""

from __future__ import annotations

import os
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from agents.knowledge_rag import KnowledgeRAGAgent
from agents.ticket_handler import TicketHandlerAgent, TicketStore
from agents.compliance_checker import ComplianceCheckerAgent
from agents.human_handoff import HumanHandoffStore, HUMAN_HANDOFF_SYSTEM_PROMPT
from memory.working_memory import WorkingMemory
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from tracing.otel_config import trace_agent_call


# --- State definition ---

class AgentState(TypedDict):
    """Supervisor global state"""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    intent: str
    sub_results: dict[str, Any]
    compliance_passed: bool
    final_response: str
    current_agent: str
    retry_count: int
    auth_token: str  # JWT token, passed through to MCP tools for backend API calls
    auth_type: str   # "admin" or "user", determines available tools and permissions


# --- Supervisor Node ---

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor of a food delivery customer service system.

Your responsibilities:
1. Analyze user intent and decide which sub-agent to route to
2. Synthesize sub-agent results into a final response
3. Ensure all responses go through compliance review
4. Adapt to the user type (admin vs consumer)

Available sub-agents:
- knowledge_rag: Knowledge base Q&A (menu info, policies, FAQ)
- ticket_handler: Order query and order actions
- compliance_checker: Compliance review and sensitive content detection
- human_handoff: Transfer to human customer service agent

Admin tools (via ticket_handler, admin only):
- order_query: Search all orders by ID, phone, status
- order_action: Confirm/reject/cancel/deliver/complete any order
- menu_query: Query dishes, setmeals, categories
- business_data: Business statistics and dashboard
- shop_status: Get/set shop open/closed status

Consumer tools (via ticket_handler, consumer only):
- user_order_query: Search own orders by status, view order detail
- user_order_action: Cancel order, remind merchant, re-order
- user_menu_query: Browse menu (dishes, setmeals, categories)
- user_shop_info: Check shop status, phone, address

Routing rules:
- If user asks about their own orders (status, detail, "my orders"), route to ticket_handler
- If user asks about menu, dishes, recommendations, policies, FAQ, route to knowledge_rag
- If user asks to cancel/remind/re-order their own orders, route to ticket_handler
- If user (consumer) asks to confirm/reject/deliver/set shop status → route to knowledge_rag with explanation that this is admin-only
- If user requests human agent ("人工"/"转人工"/"人工客服"/"找真人"/"有人吗"/"我要人工"), route to human_handoff
- If user expresses frustration/anger and wants to talk to a real person, route to human_handoff
- If request contains sensitive/inappropriate content, route to compliance_checker

Based on the user message, decide the next agent. Output ONLY one of: knowledge_rag, ticket_handler, compliance_checker, human_handoff.
"""

SYNTHESIZE_SYSTEM_PROMPT = """你是一个专业、友好的外卖客服。你的任务是根据用户的问题和系统查询到的数据，生成自然、贴心、有帮助的回复。

## 回复规范
1. **理解用户真实意图**：用户可能用口语化表达（如"还要多久"、"超时了怎么办"、"怎么还没到"），要理解其背后的真实需求
2. **结合数据回答**：利用查询结果中的具体信息（订单状态、金额、时间等）来回答，让回复更具体
3. **语气亲切自然**：像真人客服一样说话，不要机械地罗列数据，每次回复要有变化
4. **主动提供帮助**：在回答问题的同时，主动告知用户可以做什么（如催单、取消、联系商家等）
5. **简洁有力**：不要啰嗦，直击要点

## 订单状态对照
- 1 待付款 → 订单还未支付，请尽快完成支付
- 2 待接单 → 商家还未接单，请耐心等待
- 3 已接单 → 商家已接单，正在准备中
- 4 派送中 → 骑手已取餐，正在配送途中
- 5 已完成 → 订单已送达并完成
- 6 已取消 → 订单已取消

## 常见场景回复要点
- 用户问"还要多久"/"什么时候到"：根据订单状态给出预估，派送中可说"骑手正在路上，预计很快到达"，待接单可说"商家接单后约30-50分钟送达"
- 用户问"超时了怎么办"：先共情，告知可联系客服或申请退款
- 用户催单：告知已催促商家，请耐心等待
- 用户想取消：确认是否需要取消，告知取消政策和退款时间

请根据用户问题和数据，直接输出最终回复内容（不要加任何前缀说明）。
"""


class SupervisorNode:
    """Supervisor decision node"""

    def __init__(self, llm: ChatOpenAI, working_memory: WorkingMemory):
        self.llm = llm
        self.working_memory = working_memory

    @trace_agent_call("supervisor")
    async def route_decision(self, state: AgentState) -> AgentState:
        """Analyze user intent and decide routing via LLM"""
        messages = state["messages"]
        session_id = state.get("session_id", "default")
        auth_type = state.get("auth_type", "admin")
        context = self.working_memory.get_context(session_id)
        routing_prompt = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            SystemMessage(content=f"Current user type: {auth_type} ({'administrator with full privileges' if auth_type == 'admin' else 'consumer - can only query own orders, cancel, remind, re-order, and browse menu'})"),
            SystemMessage(content=f"Working memory: {context}"),
            *messages,
            HumanMessage(content=(
                "Based on the user's latest message and context, decide which agent to route to. "
                "Output ONLY one of: knowledge_rag, ticket_handler, compliance_checker, human_handoff"
            )),
        ]

        response = await self.llm.ainvoke(routing_prompt)
        intent = response.content.strip().lower()

        valid_intents = {"knowledge_rag", "ticket_handler", "compliance_checker", "human_handoff"}
        if intent not in valid_intents:
            intent = "knowledge_rag"

        self.working_memory.update(session_id, {"last_intent": intent})

        return {
            **state,
            "intent": intent,
            "current_agent": "supervisor",
        }

    @trace_agent_call("supervisor_synthesize")
    async def synthesize_response(self, state: AgentState) -> AgentState:
        """Use LLM to synthesize sub-agent results into a natural, context-aware response"""
        sub_results = state.get("sub_results", {})
        compliance_passed = state.get("compliance_passed", True)
        messages = state.get("messages", [])

        if not compliance_passed:
            final_response = (
                "抱歉，您的问题涉及敏感内容，已转接人工客服处理，请稍后查看回复。"
            )
        else:
            # Collect raw data from sub-agents
            result_parts = []
            for agent_name, result in sub_results.items():
                if agent_name == "compliance":
                    continue  # skip compliance metadata
                if isinstance(result, str) and result.strip():
                    result_parts.append(result)

            raw_data = "\n".join(result_parts) if result_parts else "无查询结果"

            # Get the user's original question
            user_question = ""
            for m in reversed(messages):
                if hasattr(m, 'type') and m.type == 'human':
                    user_question = m.content
                    break

            # Use LLM to generate a natural response
            if result_parts:
                synth_messages = [
                    SystemMessage(content=SYNTHESIZE_SYSTEM_PROMPT),
                    HumanMessage(content=f"用户问题：{user_question}\n\n查询到的数据：\n{raw_data}\n\n请根据以上信息生成客服回复。"),
                ]
                llm_response = await self.llm.ainvoke(synth_messages)
                final_response = llm_response.content.strip()
            else:
                final_response = "抱歉，暂时无法处理您的请求，请稍后重试。"

        return {
            **state,
            "final_response": final_response,
            "messages": [AIMessage(content=final_response)],
        }


# --- Human Handoff Node ---

class HumanHandoffNode:
    """人工转接节点 — 用户要求人工服务时触发"""

    def __init__(self, llm: ChatOpenAI, handoff_store: HumanHandoffStore):
        self.llm = llm
        self.handoff_store = handoff_store

    @trace_agent_call("human_handoff")
    async def process(self, state: AgentState) -> AgentState:
        """处理人工转接请求"""
        messages = state.get("messages", [])
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id", "anonymous")

        # Get user's last message
        user_question = ""
        for m in reversed(messages):
            if hasattr(m, 'type') and m.type == 'human':
                user_question = m.content
                break

        # Escalate the session
        self.handoff_store.escalate(session_id, user_id)

        # Generate handoff reply using LLM
        handoff_messages = [
            SystemMessage(content=HUMAN_HANDOFF_SYSTEM_PROMPT),
            HumanMessage(content=f"用户说: {user_question}\n请生成转接人工客服的回复。"),
        ]
        llm_response = await self.llm.ainvoke(handoff_messages)
        reply = llm_response.content.strip()

        return {
            **state,
            "sub_results": {
                **state.get("sub_results", {}),
                "human_handoff": reply,
            },
        }


# --- Routing functions ---

def route_to_agent(state: AgentState) -> str:
    """Route to the correct agent node based on intent"""
    intent = state.get("intent", "knowledge_rag")
    route_map = {
        "knowledge_rag": "knowledge_rag",
        "ticket_handler": "ticket_handler",
        "compliance_checker": "compliance_check",
        "human_handoff": "human_handoff",
    }
    return route_map.get(intent, "knowledge_rag")


def should_check_compliance(state: AgentState) -> str:
    """All responses must go through compliance review"""
    return "compliance_check"


# --- Build Graph ---

def create_supervisor_graph(
    llm: ChatOpenAI | None = None,
    working_memory: WorkingMemory | None = None,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    ticket_store: TicketStore | None = None,
    mcp_server: Any = None,
    handoff_store: HumanHandoffStore | None = None,
    enable_checkpointing: bool = True,
) -> StateGraph:
    """
    Build the Supervisor-orchestrated multi-agent StateGraph.

    This is the core entry point of the system, connecting 4 sub-agents
    via a directed graph. The Supervisor node handles routing and synthesis.

    Args:
        llm: Language model instance
        working_memory: Working memory
        short_term_memory: Short-term memory
        long_term_memory: Long-term memory
        ticket_store: Ticket store
        mcp_server: MCP tool server
        handoff_store: Human handoff session store
        enable_checkpointing: Enable checkpointing (supports resume)
    """
    if llm is None:
        model_name = os.getenv("MODEL_NAME", "qwen3.7-plus")
        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"

        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)

        llm_kwargs = {
            "model": model_name,
            "temperature": 0,
            "base_url": base_url,
        }
        if api_key:
            llm_kwargs["api_key"] = api_key

        llm = ChatOpenAI(**llm_kwargs)
    if working_memory is None:
        working_memory = WorkingMemory()
    if ticket_store is None:
        ticket_store = TicketStore()
    if handoff_store is None:
        handoff_store = HumanHandoffStore()

    supervisor = SupervisorNode(llm, working_memory)

    knowledge_agent = KnowledgeRAGAgent(llm, long_term_memory)
    ticket_agent = TicketHandlerAgent(llm, ticket_store=ticket_store, mcp_server=mcp_server)
    compliance_agent = ComplianceCheckerAgent(llm)
    human_handoff_agent = HumanHandoffNode(llm, handoff_store)

    graph = StateGraph(AgentState)

    graph.add_node("supervisor_route", supervisor.route_decision)
    graph.add_node("knowledge_rag", knowledge_agent.process)
    graph.add_node("ticket_handler", ticket_agent.process)
    graph.add_node("compliance_check", compliance_agent.process)
    graph.add_node("human_handoff", human_handoff_agent.process)
    graph.add_node("synthesize", supervisor.synthesize_response)

    graph.set_entry_point("supervisor_route")

    graph.add_conditional_edges(
        "supervisor_route",
        route_to_agent,
        {
            "knowledge_rag": "knowledge_rag",
            "ticket_handler": "ticket_handler",
            "compliance_check": "compliance_check",
            "human_handoff": "human_handoff",
        },
    )

    graph.add_edge("knowledge_rag", "compliance_check")
    graph.add_edge("ticket_handler", "compliance_check")
    graph.add_edge("human_handoff", "compliance_check")
    graph.add_edge("compliance_check", "synthesize")
    graph.add_edge("synthesize", END)

    checkpointer = MemorySaver() if enable_checkpointing else None
    compiled = graph.compile(checkpointer=checkpointer)

    return compiled
