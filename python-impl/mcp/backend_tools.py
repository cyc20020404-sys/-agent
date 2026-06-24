"""
MCP 后端工具 — 对接 Spring Boot 外卖系统真实 API

替代 mcp_server.py 中 create_default_tools() 的 4 个硬编码工具。
每个工具的 handler 通过 BackendClient 调用 Spring Boot 管理端 API。
"""
from __future__ import annotations
import re


def _mask_phone(text: str) -> str:
    """Mask phone numbers: 13812345678 -> 138****5678"""
    return re.sub(r'(1[3-9]\d)\d{4}(\d{4})', r'\1****\2', text)

from datetime import datetime
from typing import Any

from mcp.backend_client import BackendClient, BackendAuthError, BackendApiError
from mcp.mcp_server import MCPToolServer, ToolDefinition

# 订单状态码映射
ORDER_STATUS_MAP: dict[int, str] = {
    1: "待付款",
    2: "待接单",
    3: "已接单",
    4: "派送中",
    5: "已完成",
    6: "已取消",
}

# 支付状态映射
PAY_STATUS_MAP: dict[int, str] = {
    0: "未支付",
    1: "已支付",
    2: "退款中",
}


def _format_orders(records: list[dict]) -> str:
    """将后端订单列表格式化为可读文本"""
    if not records:
        return "暂无匹配的订单记录。"

    lines = [f"共找到 {len(records)} 笔订单：\n"]
    for i, order in enumerate(records, 1):
        order_id = order.get("id", "?")
        number = order.get("number", "?")
        status = ORDER_STATUS_MAP.get(order.get("status", 0), "未知")
        amount = order.get("amount", 0)
        order_time = order.get("orderTime", "?")
        phone = order.get("phone", "?")
        address = order.get("address", "?")

        lines.append(
            f"{i}. 订单#{order_id} | {number}\n"
            f"   状态: {status} | 金额: ¥{amount:.2f} | 下单时间: {order_time}\n"
            f"   手机号: {phone} | 地址: {address}\n"
        )

    return _mask_phone("\n".join(lines))


def _format_order_detail(order: dict) -> str:
    """将后端订单详情格式化为可读文本"""
    order_id = order.get("id", "?")
    number = order.get("number", "?")
    status = ORDER_STATUS_MAP.get(order.get("status", 0), "未知")
    amount = order.get("amount", 0)
    order_time = order.get("orderTime", "?")
    phone = order.get("phone", "?")
    address = order.get("address", "?")
    userName = order.get("userName", "?")
    remark = order.get("remark", "无")

    lines = [
        f"📋 订单详情 | #{order_id}",
        f"单号: {number}",
        f"状态: {status}",
        f"金额: ¥{amount:.2f}",
        f"下单时间: {order_time}",
        f"客户: {userName}",
        f"手机: {phone}",
        f"地址: {address}",
        f"备注: {remark}",
    ]

    # 订单明细
    detail_list = order.get("orderDetailList") or []
    if detail_list:
        lines.append("\n🍽️ 订单商品:")
        for item in detail_list:
            dish_name = item.get("name", "?")
            qty = item.get("number", 1)
            price = item.get("amount", 0)
            lines.append(f"  - {dish_name} x{qty} ¥{price:.2f}")

    return _mask_phone("\n".join(lines))


# ─── 工具注册入口 ───


def create_backend_tools(
    server: MCPToolServer,
    backend_client: BackendClient,
) -> None:
    """注册所有对接外卖后端的 MCP 工具"""

    # ── 1. order_query ──
    @server.register(
        name="order_query",
        description="查询订单信息：可按订单号、手机号、状态等条件搜索订单，或查看单个订单详情",
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "订单ID（数据库主键），指定后返回该订单详情",
                },
                "phone": {
                    "type": "string",
                    "description": "客户手机号，支持模糊匹配",
                },
                "number": {
                    "type": "string",
                    "description": "订单编号",
                },
                "status": {
                    "type": "integer",
                    "description": "订单状态: 1待付款 2待接单 3已接单 4派送中 5已完成 6已取消",
                },
                "page": {"type": "integer", "description": "页码，默认1"},
                "pageSize": {"type": "integer", "description": "每页条数，默认10"},
                "token": {"type": "string", "description": "管理员JWT认证令牌"},
            },
        },
        category="order",
        requires_auth=True,
    )
    async def order_query(
        order_id: int | None = None,
        phone: str | None = None,
        number: str | None = None,
        status: int | None = None,
        page: int = 1,
        pageSize: int = 10,
        token: str | None = None,
    ) -> str:
        if order_id is not None:
            try:
                detail = await backend_client.get(
                    f"/order/details/{order_id}", token=token
                )
                return _format_order_detail(detail)
            except BackendApiError as e:
                return f"查询订单 #{order_id} 失败：{e}"

        # 搜索
        params: dict[str, Any] = {"page": page, "pageSize": pageSize}
        if phone:
            params["phone"] = phone
        if number:
            params["number"] = number
        if status is not None:
            params["status"] = status

        try:
            result = await backend_client.get(
                "/order/conditionSearch", params=params, token=token
            )
            records = result.get("records", []) if isinstance(result, dict) else []
            return _format_orders(records)
        except BackendApiError as e:
            return f"搜索订单失败：{e}"

    # ── 2. order_action ──
    @server.register(
        name="order_action",
        description="订单操作：接单、拒单、取消、派送、完成。操作前请先确认订单ID正确。",
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["confirm", "reject", "cancel", "delivery", "complete"],
                    "description": "操作类型: confirm接单 reject拒单 cancel取消 delivery派送 complete完成",
                },
                "order_id": {
                    "type": "integer",
                    "description": "订单ID（数据库主键）",
                },
                "reason": {
                    "type": "string",
                    "description": "拒单/取消原因（action为reject或cancel时需要）",
                },
                "token": {"type": "string", "description": "管理员JWT认证令牌"},
            },
            "required": ["action", "order_id"],
        },
        category="order",
        requires_auth=True,
    )
    async def order_action(
        action: str,
        order_id: int,
        reason: str | None = None,
        token: str | None = None,
    ) -> str:
        action_labels: dict[str, str] = {
            "confirm": "接单",
            "reject": "拒单",
            "cancel": "取消",
            "delivery": "派送",
            "complete": "完成",
        }

        label = action_labels.get(action, action)

        try:
            if action == "confirm":
                await backend_client.put(
                    "/order/confirm", {"id": order_id}, token=token
                )
            elif action == "reject":
                await backend_client.put(
                    "/order/rejection",
                    {"id": order_id, "rejectionReason": reason or "无"},
                    token=token,
                )
            elif action == "cancel":
                await backend_client.put(
                    "/order/cancel",
                    {"id": order_id, "cancelReason": reason or "无"},
                    token=token,
                )
            elif action == "delivery":
                await backend_client.put(f"/order/delivery/{order_id}", token=token)
            elif action == "complete":
                await backend_client.put(f"/order/complete/{order_id}", token=token)
            else:
                return f"不支持的操作类型: {action}"

            # 操作成功后获取最新订单详情
            detail = await backend_client.get(
                f"/order/details/{order_id}", token=token
            )
            new_status = ORDER_STATUS_MAP.get(
                detail.get("status", 0) if isinstance(detail, dict) else 0, "未知"
            )
            return f"✅ 订单 #{order_id} 已{label}，当前状态: {new_status}"
        except BackendAuthError:
            return "操作失败：认证已过期，请重新登录后再试。"
        except BackendApiError as e:
            return f"操作失败：{e}"

    # ── 3. menu_query ──
    @server.register(
        name="menu_query",
        description="查询菜品、套餐、分类信息",
        input_schema={
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["dish", "setmeal", "category", "all"],
                    "description": "查询类型: dish菜品 setmeal套餐 category分类 all全部",
                },
                "category_id": {
                    "type": "integer",
                    "description": "分类ID（查菜品或套餐时可选）",
                },
                "token": {"type": "string", "description": "管理员JWT认证令牌"},
            },
            "required": ["query_type"],
        },
        category="menu",
        requires_auth=True,
    )
    async def menu_query(
        query_type: str,
        category_id: int | None = None,
        token: str | None = None,
    ) -> str:
        try:
            lines: list[str] = []

            if query_type in ("dish", "all"):
                params = {}
                if category_id:
                    params["categoryId"] = category_id
                dishes = await backend_client.get("/dish/list", params=params, token=token)
                dish_list = dishes if isinstance(dishes, list) else dishes.get("records", [])
                lines.append("🍽️ **菜品列表**：")
                if dish_list:
                    for d in dish_list:
                        status_label = "上架" if d.get("status") == 1 else "下架"
                        lines.append(
                            f"  - {d.get('name', '?')} | ¥{d.get('price', 0):.2f} | {status_label}"
                        )
                else:
                    lines.append("  (暂无菜品)")

            if query_type in ("setmeal", "all"):
                params = {"page": 1, "pageSize": 50}
                if category_id:
                    params["categoryId"] = category_id
                result = await backend_client.get(
                    "/setmeal/page", params=params, token=token
                )
                sm_list = result.get("records", []) if isinstance(result, dict) else []
                lines.append("\n📦 **套餐列表**：")
                if sm_list:
                    for s in sm_list:
                        status_label = "上架" if s.get("status") == 1 else "下架"
                        lines.append(
                            f"  - {s.get('name', '?')} | ¥{s.get('price', 0):.2f} | {status_label}"
                        )
                else:
                    lines.append("  (暂无套餐)")

            if query_type in ("category", "all"):
                # 分类信息（type=1 菜品分类）
                try:
                    cats = await backend_client.get(
                        "/category/list", params={"type": 1}, token=token
                    )
                except Exception:
                    cats = []
                if cats:
                    lines.append("\n📂 **菜品分类**：")
                    for c in cats:
                        lines.append(f"  - {c.get('name', '?')} (ID: {c.get('id', '?')})")

            return "\n".join(lines) if lines else "暂无菜单数据。"

        except BackendApiError as e:
            return f"查询菜单失败：{e}"

    # ── 4. business_data ──
    @server.register(
        name="business_data",
        description="查询营业数据：今日概览、订单统计、菜品/套餐统计、销售TOP10",
        input_schema={
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "enum": ["overview", "orders", "dishes", "setmeals", "top10"],
                    "description": "数据类型: overview今日概览 orders订单统计 dishes菜品统计 setmeals套餐统计 top10销量排行",
                },
                "token": {"type": "string", "description": "管理员JWT认证令牌"},
            },
            "required": ["data_type"],
        },
        category="business",
        requires_auth=True,
    )
    async def business_data(
        data_type: str,
        token: str | None = None,
    ) -> str:
        try:
            if data_type == "overview":
                data = await backend_client.get(
                    "/workspace/businessData", token=token
                )
                return (
                    f"📊 今日营业概览:\n"
                    f"  营业额: ¥{data.get('turnover', 0):.2f}\n"
                    f"  有效订单: {data.get('validOrderCount', 0)} 单\n"
                    f"  订单完成率: {data.get('orderCompletionRate', 0)}%\n"
                    f"  客单价: ¥{data.get('unitPrice', 0):.2f}\n"
                    f"  新增用户: {data.get('newUsers', 0)} 人"
                )

            elif data_type == "orders":
                overview = await backend_client.get(
                    "/workspace/overviewOrders", token=token
                )
                stats = await backend_client.get("/order/statistics", token=token)
                return (
                    f"📋 订单概况:\n"
                    f"  待接单: {stats.get('toBeConfirmed', 0)} 单\n"
                    f"  已接单: {stats.get('confirmed', 0)} 单\n"
                    f"  派送中: {stats.get('deliveryInProgress', 0)} 单\n"
                    f"  待处理: {overview.get('waitingOrders', 0)} 单\n"
                    f"  已完成: {overview.get('completedOrders', 0)} 单\n"
                    f"  已取消: {overview.get('cancelledOrders', 0)} 单"
                )

            elif data_type == "dishes":
                overview = await backend_client.get(
                    "/workspace/overviewDishes", token=token
                )
                return (
                    f"🍽️ 菜品统计:\n"
                    f"  在售: {overview.get('sold', 0)} 种\n"
                    f"  停售: {overview.get('discontinued', 0)} 种"
                )

            elif data_type == "setmeals":
                overview = await backend_client.get(
                    "/workspace/overviewSetmeals", token=token
                )
                return (
                    f"📦 套餐统计:\n"
                    f"  在售: {overview.get('sold', 0)} 种\n"
                    f"  停售: {overview.get('discontinued', 0)} 种"
                )

            elif data_type == "top10":
                today = datetime.now().strftime("%Y-%m-%d")
                data = await backend_client.get(
                    "/report/top10",
                    params={"begin": today, "end": today},
                    token=token,
                )
                name_list = data.get("nameList", "")
                number_list = data.get("numberList", "")
                names = name_list.split(",") if name_list else []
                nums = number_list.split(",") if number_list else []
                lines = ["🏆 今日销量 TOP10:"]
                for i, (name, num) in enumerate(zip(names, nums), 1):
                    lines.append(f"  {i}. {name} — {num} 份")
                return "\n".join(lines)

            else:
                return f"不支持的数据类型: {data_type}"

        except BackendApiError as e:
            return f"查询营业数据失败：{e}"

    # ── 5. shop_status ──
    @server.register(
        name="shop_status",
        description="查询或设置店铺营业状态（1营业中 0打烊）",
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "set"],
                    "description": "get查询状态 set设置状态",
                },
                "status": {
                    "type": "integer",
                    "enum": [0, 1],
                    "description": "0打烊 1营业中（action为set时需要）",
                },
                "token": {"type": "string", "description": "管理员JWT认证令牌"},
            },
            "required": ["action"],
        },
        category="shop",
        requires_auth=True,
    )
    async def shop_status(
        action: str,
        status: int | None = None,
        token: str | None = None,
    ) -> str:
        try:
            if action == "get":
                current = await backend_client.get("/shop/status", token=token)
                label = "营业中 🟢" if current == 1 else "已打烊 🔴"
                return f"当前店铺状态: {label}"

            elif action == "set":
                if status is None:
                    return "请指定目标状态: 0=打烊, 1=营业中"
                await backend_client.put(f"/shop/{status}", token=token)
                label = "营业中 🟢" if status == 1 else "已打烊 🔴"
                return f"✅ 店铺状态已更新为: {label}"

            else:
                return f"不支持的操作: {action}"

        except BackendApiError as e:
            return f"操作失败：{e}"

    return server
