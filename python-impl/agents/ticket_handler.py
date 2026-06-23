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
    "order_query": {
        "assigned_queue": "order_workflow",
        "current_stage": "order_lookup",
        "handoff_mode": "automatic",
    },
    "order_action": {
        "assigned_queue": "order_workflow",
        "current_stage": "order_processing",
        "handoff_mode": "automatic",
    },
    "menu_query": {
        "assigned_queue": "menu_workflow",
        "current_stage": "menu_lookup",
        "handoff_mode": "automatic",
    },
    "business_data": {
        "assigned_queue": "report_workflow",
        "current_stage": "data_lookup",
        "handoff_mode": "automatic",
    },
    "shop_status": {
        "assigned_queue": "shop_workflow",
        "current_stage": "status_management",
        "handoff_mode": "automatic",
    },
    "general": {
        "assigned_queue": "general_support",
        "current_stage": "triage",
        "handoff_mode": "manual_review",
    },
    "general": {
        "assigned_queue": "manual_support",
        "current_stage": "manual_triage",
        "handoff_mode": "manual_review",
    },
}


TICKET_SYSTEM_PROMPT = """你是一个专业的外卖订单处理Agent，负责处理订单查询和订单操作。

你的职责：
1. 分析用户需求，判断是查询订单还是执行订单操作
2. 提取关键信息（订单ID、手机号、操作类型等）
3. 通过MCP工具调用后端API完成操作

支持的操作类型：
- order_query: 查询订单（按订单ID、手机号、状态、订单编号等条件）
- order_action: 订单操作（接单confirm、拒单reject、取消cancel、派送delivery、完成complete）
  - confirm 接单不需要reason
  - reject 拒单需要 rejectionReason
  - cancel 取消需要 cancelReason
  - delivery 派送不需要reason
  - complete 完成不需要reason
- menu_query: 查询菜品/套餐/分类
- business_data: 查询营业数据（概览、订单统计、TOP10）
- shop_status: 查询或设置店铺营业状态

订单状态码：
- 1: 待付款
- 2: 待接单
- 3: 已接单
- 4: 派送中
- 5: 已完成
- 6: 已取消

请以JSON格式返回：
{
    "action": "order_query|order_action|menu_query|business_data|shop_status",
    "operation": "具体的子操作类型",
    "order_id": 订单ID数字,
    "phone": "手机号",
    "reason": "拒单或取消的原因",
    "summary": "用户需求的简短总结"
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

    def __init__(self, llm: ChatOpenAI, ticket_store: TicketStore | None = None, mcp_server=None):
        self.llm = llm
        self.mcp_server = mcp_server
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
        """分析用户需求，提取外卖订单操作信息"""
        # 检测订单ID模式（数字类型）
        import re
        order_id_match = re.search(r'(?:订单|ID|id|编号)\s*[:：#]?\s*(\d+)', user_message)
        phone_match = re.search(r'1[3-9]\d{9}', user_message)
        number_match = re.search(r'(?:编号|单号|number)[:：\s]*(\w+)', user_message, re.IGNORECASE)

        extracted: dict = {}
        if order_id_match:
            extracted["order_id"] = int(order_id_match.group(1))
        if phone_match:
            extracted["phone"] = phone_match.group()
        if number_match:
            extracted["number"] = number_match.group(1)

        messages = [
            SystemMessage(content=TICKET_SYSTEM_PROMPT),
            HumanMessage(content=f"用户消息: {user_message}\n已提取的上下文: {extracted}"),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            import json
            ticket_info = json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            ticket_info = {
                "action": "order_query",
                "summary": user_message[:100],
            }

        # 合并提取的订单ID
        if "order_id" not in ticket_info and "order_id" in extracted:
            ticket_info["order_id"] = extracted["order_id"]
        if "phone" not in ticket_info and "phone" in extracted:
            ticket_info["phone"] = extracted["phone"]

        return ticket_info

    @trace_agent_call("ticket_execute")
    async def execute_action(self, ticket_info: dict, user_id: str, auth_token: str = "", auth_type: str = "admin") -> str:
        """通过MCP工具执行订单操作（区分admin/user工具）"""
        action = ticket_info.get("action", "order_query")

        if self.mcp_server is None:
            return "MCP工具服务未初始化，无法执行操作。"

        # ── 用户端：只能调用 user_* 工具 ──
        if auth_type == "user":
            if action == "order_query":
                result = await self.mcp_server.call_tool("user_order_query", {
                    "order_id": ticket_info.get("order_id"),
                    "status": ticket_info.get("status"),
                    "page": 1,
                    "pageSize": 10,
                    "token": auth_token,
                })
            elif action == "order_action":
                op = ticket_info.get("operation", "reminder")
                if op in ("confirm", "reject", "delivery", "complete"):
                    return "抱歉，该操作（接单/拒单/派送/完成）仅限管理后台进行。您可以使用：取消订单、催单、再来一单。"
                result = await self.mcp_server.call_tool("user_order_action", {
                    "action": op,
                    "order_id": ticket_info.get("order_id"),
                    "token": auth_token,
                })
            elif action == "menu_query":
                result = await self.mcp_server.call_tool("user_menu_query", {
                    "query_type": ticket_info.get("operation", "all"),
                    "token": auth_token,
                })
            elif action == "shop_status":
                result = await self.mcp_server.call_tool("user_shop_info", {
                    "info_type": ticket_info.get("operation", "all"),
                    "token": auth_token,
                })
            else:
                result = await self.mcp_server.call_tool("user_order_query", {
                    "page": 1, "pageSize": 10, "token": auth_token,
                })
        # ── 管理员端：使用 admin 工具 ──
        else:
            if action == "order_query":
                result = await self.mcp_server.call_tool("order_query", {
                    "order_id": ticket_info.get("order_id"),
                    "phone": ticket_info.get("phone"),
                    "number": ticket_info.get("number"),
                    "status": ticket_info.get("status"),
                    "page": 1, "pageSize": 10, "token": auth_token,
                })
            elif action == "order_action":
                result = await self.mcp_server.call_tool("order_action", {
                    "action": ticket_info.get("operation", "confirm"),
                    "order_id": ticket_info.get("order_id"),
                    "reason": ticket_info.get("reason", ""),
                    "token": auth_token,
                })
            elif action == "menu_query":
                result = await self.mcp_server.call_tool("menu_query", {
                    "query_type": ticket_info.get("operation", "all"),
                    "token": auth_token,
                })
            elif action == "business_data":
                result = await self.mcp_server.call_tool("business_data", {
                    "data_type": ticket_info.get("operation", "overview"),
                    "token": auth_token,
                })
            elif action == "shop_status":
                result = await self.mcp_server.call_tool("shop_status", {
                    "action": ticket_info.get("operation", "get"),
                    "status": ticket_info.get("status"),
                    "token": auth_token,
                })
            else:
                result = await self.mcp_server.call_tool("order_query", {
                    "phone": ticket_info.get("phone"),
                    "page": 1, "pageSize": 10, "token": auth_token,
                })

        if result.success:
            return str(result.result)
        return f"操作失败：{result.error}"

    @trace_agent_call("ticket_handler_process")
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """作为Graph节点处理状态——通过MCP工具调用后端API"""
        messages = state.get("messages", [])
        user_id = state.get("user_id", "anonymous")
        auth_token = state.get("auth_token", "")
        auth_type = state.get("auth_type", "admin")

        if not messages:
            return state

        last_message = messages[-1].content
        ticket_info = await self.analyze_request(last_message)
        result = await self.execute_action(ticket_info, user_id, auth_token, auth_type)

        return {
            **state,
            "sub_results": {
                **state.get("sub_results", {}),
                "ticket_handler": result,
            },
        }
