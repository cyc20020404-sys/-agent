"""
工单处理Agent — 工单CRUD与流转
负责创建、查询、更新工单，对接工单系统，处理退款/理赔/开户等业务办理类需求。
通过MCP工具协议调用外部工单系统。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tracing.otel_config import trace_agent_call


class TicketStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


QUEUE_CONFIG: dict[str, dict[str, str]] = {
    "refund": {
        "assigned_queue": "refund_workflow",
        "current_stage": "refund_intake",
        "handoff_mode": "automatic",
    },
    "claim": {
        "assigned_queue": "claim_review_queue",
        "current_stage": "claim_review",
        "handoff_mode": "manual_review",
    },
    "account_open": {
        "assigned_queue": "account_open_workflow",
        "current_stage": "account_verification",
        "handoff_mode": "automatic",
    },
    "account_change": {
        "assigned_queue": "account_service_queue",
        "current_stage": "change_request_review",
        "handoff_mode": "manual_review",
    },
    "complaint": {
        "assigned_queue": "manual_support",
        "current_stage": "manual_triage",
        "handoff_mode": "manual_review",
    },
    "general": {
        "assigned_queue": "manual_support",
        "current_stage": "manual_triage",
        "handoff_mode": "manual_review",
    },
}


TICKET_SYSTEM_PROMPT = """你是一个专业的工单处理Agent，负责处理客户的业务办理请求。

你的职责：
1. 分析用户需求，判断是否需要创建工单
2. 提取工单关键信息（类型、优先级、描述）
3. 创建工单并返回工单号
4. 查询现有工单状态

工单类型：
- refund: 退款申请
- claim: 理赔申请
- account_open: 开户申请
- account_change: 账户变更
- complaint: 投诉工单
- general: 通用工单

优先级判断规则：
- urgent: 资金安全、账户被盗
- high: 退款超时、理赔争议
- medium: 常规业务办理
- low: 信息咨询类

请以JSON格式返回工单信息：
{
    "action": "create|query|update",
    "ticket_type": "refund|claim|account_open|...",
    "priority": "low|medium|high|urgent",
    "summary": "工单摘要",
    "details": "详细描述"
}
"""


class TicketStore:
    """内存工单存储（生产环境应替换为数据库）"""

    def __init__(self):
        self._tickets: dict[str, dict] = {}

    def create(self, ticket_type: str, priority: str, summary: str, details: str, user_id: str) -> dict:
        ticket_id = f"TK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        ticket = {
            "ticket_id": ticket_id,
            "type": ticket_type,
            "priority": priority,
            "status": TicketStatus.CREATED.value,
            "summary": summary,
            "details": details,
            "user_id": user_id,
            "assigned_queue": "unassigned",
            "current_stage": "waiting_assignment",
            "handoff_mode": "pending",
            "last_event": "ticket_created",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._tickets[ticket_id] = ticket
        return ticket

    def query(self, ticket_id: str) -> dict | None:
        return self._tickets.get(ticket_id)

    def query_by_user(self, user_id: str) -> list[dict]:
        return [t for t in self._tickets.values() if t["user_id"] == user_id]

    def update_status(self, ticket_id: str, status: str) -> dict | None:
        ticket = self._tickets.get(ticket_id)
        if ticket:
            ticket["status"] = status
            ticket["updated_at"] = datetime.now().isoformat()
        return ticket

    def update_ticket(self, ticket_id: str, **fields: Any) -> dict | None:
        ticket = self._tickets.get(ticket_id)
        if ticket:
            ticket.update(fields)
            ticket["updated_at"] = datetime.now().isoformat()
        return ticket


class TicketHandlerAgent:
    """工单处理Agent"""

    TICKET_ID_PATTERN = r"TK-\d{8}-[A-Z0-9]{6}"

    def __init__(self, llm: ChatOpenAI, ticket_store: TicketStore | None = None):
        self.llm = llm
        self.ticket_store = ticket_store or TicketStore()

    def _extract_ticket_id(self, user_message: str) -> str | None:
        match = re.search(self.TICKET_ID_PATTERN, user_message)
        return match.group(0) if match else None

    def _get_queue_config(self, ticket_type: str) -> dict[str, str]:
        return QUEUE_CONFIG.get(ticket_type, QUEUE_CONFIG["general"])

    def _label_queue(self, queue_name: str) -> str:
        return {
            "refund_workflow": "退款处理工作流",
            "claim_review_queue": "理赔审核队列",
            "account_open_workflow": "开户处理工作流",
            "account_service_queue": "账户服务队列",
            "manual_support": "人工客服队列",
            "unassigned": "待分配",
        }.get(queue_name, queue_name)

    def _label_stage(self, stage_name: str) -> str:
        return {
            "waiting_assignment": "等待分配",
            "refund_intake": "退款受理",
            "claim_review": "理赔审核",
            "account_verification": "开户资料校验",
            "change_request_review": "账户变更审核",
            "manual_triage": "人工分诊",
        }.get(stage_name, stage_name)

    def _label_handoff_mode(self, handoff_mode: str) -> str:
        return {
            "automatic": "自动处理",
            "manual_review": "人工处理",
            "pending": "待处理",
        }.get(handoff_mode, handoff_mode)

    def _handoff_ticket(self, ticket: dict) -> dict:
        queue_config = self._get_queue_config(ticket["type"])
        assigned_ticket = self.ticket_store.update_ticket(
            ticket["ticket_id"],
            assigned_queue=queue_config["assigned_queue"],
            current_stage=queue_config["current_stage"],
            handoff_mode=queue_config["handoff_mode"],
            last_event="ticket_handed_off",
        )
        if not assigned_ticket:
            return ticket

        processing_ticket = self.ticket_store.update_status(
            ticket["ticket_id"],
            TicketStatus.PROCESSING.value,
        )
        if processing_ticket:
            processing_ticket["last_event"] = "ticket_processing_started"
            return processing_ticket
        return assigned_ticket

    @trace_agent_call("ticket_analyze")
    async def analyze_request(self, user_message: str) -> dict:
        """分析用户需求，提取工单信息"""
        extracted_ticket_id = self._extract_ticket_id(user_message)
        if extracted_ticket_id:
            return {
                "action": "query",
                "ticket_id": extracted_ticket_id,
                "ticket_type": "general",
                "priority": "low",
                "summary": user_message[:100],
                "details": user_message,
            }

        messages = [
            SystemMessage(content=TICKET_SYSTEM_PROMPT),
            HumanMessage(content=f"用户消息: {user_message}"),
        ]

        response = await self.llm.ainvoke(messages)

        import json
        try:
            ticket_info = json.loads(response.content)
        except json.JSONDecodeError:
            ticket_info = {
                "action": "create",
                "ticket_type": "general",
                "priority": "medium",
                "summary": user_message[:100],
                "details": user_message,
            }

        if ticket_info.get("action") == "query" and "ticket_id" not in ticket_info and extracted_ticket_id:
            ticket_info["ticket_id"] = extracted_ticket_id

        return ticket_info

    @trace_agent_call("ticket_create")
    async def create_ticket(self, ticket_info: dict, user_id: str) -> str:
        """创建工单"""
        ticket = self.ticket_store.create(
            ticket_type=ticket_info.get("ticket_type", "general"),
            priority=ticket_info.get("priority", "medium"),
            summary=ticket_info.get("summary", ""),
            details=ticket_info.get("details", ""),
            user_id=user_id,
        )
        ticket = self._handoff_ticket(ticket)

        priority_label = {
            "low": "普通", "medium": "中等", "high": "高", "urgent": "紧急"
        }.get(ticket["priority"], "中等")

        return (
            f"工单已创建成功！\n\n"
            f"📋 工单号: {ticket['ticket_id']}\n"
            f"📝 类型: {ticket['type']}\n"
            f"⚡ 优先级: {priority_label}\n"
            f"📄 摘要: {ticket['summary']}\n"
            f"📬 处理队列: {self._label_queue(ticket['assigned_queue'])}\n"
            f"🧭 当前环节: {self._label_stage(ticket['current_stage'])}\n"
            f"🤝 处理方式: {self._label_handoff_mode(ticket['handoff_mode'])}\n"
            f"📊 当前状态: 处理中\n"
            f"🕐 创建时间: {ticket['created_at']}\n\n"
            f"您的请求已进入后续处理流程，请保存好工单号以便后续查询。"
        )

    @trace_agent_call("ticket_query")
    async def query_ticket(self, ticket_id: str) -> str:
        """查询工单状态"""
        ticket = self.ticket_store.query(ticket_id)
        if not ticket:
            return f"未找到工单号 {ticket_id}，请确认工单号是否正确。"

        status_label = {
            "created": "已创建",
            "processing": "处理中",
            "pending_review": "待审核",
            "resolved": "已解决",
            "closed": "已关闭",
            "escalated": "已升级",
        }.get(ticket["status"], ticket["status"])

        return (
            f"工单查询结果：\n\n"
            f"📋 工单号: {ticket['ticket_id']}\n"
            f"📊 状态: {status_label}\n"
            f"📝 类型: {ticket['type']}\n"
            f"📬 处理队列: {self._label_queue(ticket['assigned_queue'])}\n"
            f"🧭 当前环节: {self._label_stage(ticket['current_stage'])}\n"
            f"🤝 处理方式: {self._label_handoff_mode(ticket['handoff_mode'])}\n"
            f"📄 摘要: {ticket['summary']}\n"
            f"🕐 创建时间: {ticket['created_at']}\n"
            f"🔄 更新时间: {ticket['updated_at']}"
        )

    @trace_agent_call("ticket_handler_process")
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """作为Graph节点处理状态"""
        messages = state.get("messages", [])
        user_id = state.get("user_id", "anonymous")

        if not messages:
            return state

        last_message = messages[-1].content
        extracted_ticket_id = self._extract_ticket_id(last_message)
        ticket_info = await self.analyze_request(last_message)

        action = ticket_info.get("action", "create")
        ticket_id = ticket_info.get("ticket_id") or extracted_ticket_id

        if action == "query" and ticket_id:
            result = await self.query_ticket(ticket_id)
        else:
            result = await self.create_ticket(ticket_info, user_id)

        return {
            **state,
            "sub_results": {
                **state.get("sub_results", {}),
                "ticket_handler": result,
            },
        }
