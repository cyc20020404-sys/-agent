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
- If request contains sensitive/inappropriate content, route to compliance_checker

Based on the user message, decide the next agent. Output ONLY one of: knowledge_rag, ticket_handler, compliance_checker.
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
                "Output ONLY one of: knowledge_rag, ticket_handler, compliance_checker"
            )),
        ]

        response = await self.llm.ainvoke(routing_prompt)
        intent = response.content.strip().lower()

        valid_intents = {"knowledge_rag", "ticket_handler", "compliance_checker"}
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
        """Synthesize sub-agent results into final response"""
        sub_results = state.get("sub_results", {})
        compliance_passed = state.get("compliance_passed", True)

        if not compliance_passed:
            final_response = (
                "Sorry, your request involves sensitive content and has been "
                "transferred to human customer service. Please check for updates later."
            )
        else:
            result_parts = []
            for agent_name, result in sub_results.items():
                if isinstance(result, str) and result.strip():
                    result_parts.append(result)
            final_response = "\n\n".join(result_parts) if result_parts else "Sorry, unable to process your request at this time. Please try again later."

        return {
            **state,
            "final_response": final_response,
            "messages": [AIMessage(content=final_response)],
        }


# --- Routing functions ---

def route_to_agent(state: AgentState) -> str:
    """Route to the correct agent node based on intent"""
    intent = state.get("intent", "knowledge_rag")
    route_map = {
        "knowledge_rag": "knowledge_rag",
        "ticket_handler": "ticket_handler",
        "compliance_checker": "compliance_check",
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

    supervisor = SupervisorNode(llm, working_memory)

    knowledge_agent = KnowledgeRAGAgent(llm, long_term_memory)
    ticket_agent = TicketHandlerAgent(llm, ticket_store=ticket_store, mcp_server=mcp_server)
    compliance_agent = ComplianceCheckerAgent(llm)

    graph = StateGraph(AgentState)

    graph.add_node("supervisor_route", supervisor.route_decision)
    graph.add_node("knowledge_rag", knowledge_agent.process)
    graph.add_node("ticket_handler", ticket_agent.process)
    graph.add_node("compliance_check", compliance_agent.process)
    graph.add_node("synthesize", supervisor.synthesize_response)

    graph.set_entry_point("supervisor_route")

    graph.add_conditional_edges(
        "supervisor_route",
        route_to_agent,
        {
            "knowledge_rag": "knowledge_rag",
            "ticket_handler": "ticket_handler",
            "compliance_check": "compliance_check",
        },
    )

    graph.add_edge("knowledge_rag", "compliance_check")
    graph.add_edge("ticket_handler", "compliance_check")
    graph.add_edge("compliance_check", "synthesize")
    graph.add_edge("synthesize", END)

    checkpointer = MemorySaver() if enable_checkpointing else None
    compiled = graph.compile(checkpointer=checkpointer)

    return compiled
