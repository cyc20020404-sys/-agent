"""
MCP 用户端工具 — 对接 Spring Boot 外卖系统 /user/* API

这些工具通过 authentication header（用户 JWT）调用用户端 API，
适合微信小程序消费者场景：查自己的订单、取消/催单、浏览菜单、查店铺信息。
"""
from __future__ import annotations

import re
from typing import Any

from mcp.backend_client import BackendClient, BackendAuthError, BackendApiError
from mcp.mcp_server import MCPToolServer

def _mask_phone(text: str) -> str:
    """Mask phone numbers: 13812345678 -> 138****5678"""
    return re.sub(r'(1[3-9]\d)\d{4}(\d{4})', r'\1****\2', text)


# 订单状态码映射
ORDER_STATUS_MAP: dict[int, str] = {
    1: "待付款",
    2: "待接单",
    3: "已接单",
    4: "派送中",
    5: "已完成",
    6: "已取消",
}


def _format_user_orders(records: list[dict]) -> str:
    """将用户订单列表格式化为可读文本"""
    if not records:
        return "您暂时没有相关订单。"

    lines = [f"共 {len(records)} 笔订单：\n"]
    for i, order in enumerate(records, 1):
        order_id = order.get("id", "?")
        number = order.get("number", "?")
        status = ORDER_STATUS_MAP.get(order.get("status", 0), "未知")
        amount = order.get("amount", 0)
        order_time = order.get("orderTime", "?")
        lines.append(
            f"{i}. 订单 #{order_id} | {number}\n"
            f"   状态: {status} | 金额: ¥{amount:.2f} | 时间: {order_time}"
        )
    return _mask_phone("\n".join(lines))


def _format_user_order_detail(order: dict) -> str:
    """将订单详情格式化为可读文本"""
    order_id = order.get("id", "?")
    number = order.get("number", "?")
    status = ORDER_STATUS_MAP.get(order.get("status", 0), "未知")
    amount = order.get("amount", 0)
    order_time = order.get("orderTime", "?")
    address = order.get("address", "?")
    remark = order.get("remark", "无")

    lines = [
        f"📋 订单详情 | #{order_id}",
        f"单号: {number}",
        f"状态: {status}",
        f"金额: ¥{amount:.2f}",
        f"下单时间: {order_time}",
        f"配送地址: {address}",
        f"备注: {remark}",
    ]

    detail_list = order.get("orderDetailList") or []
    if detail_list:
        lines.append("\n订单商品:")
        for item in detail_list:
            name = item.get("name", "?")
            qty = item.get("number", 1)
            price = item.get("amount", 0)
            lines.append(f"  - {name} x{qty} ¥{price:.2f}")

    return _mask_phone("\n".join(lines))


# ─── 工具注册入口 ───


def create_user_backend_tools(
    server: MCPToolServer,
    backend_client: BackendClient,
) -> MCPToolServer:
    """注册用户端 MCP 工具集，调用 /user/* API（authentication header）"""

    # ── 1. user_order_query ──
    @server.register(
        name="user_order_query",
        description="查询当前用户的订单：按状态筛选、分页查看、查看单个订单详情",
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "订单ID，指定后返回该订单详情",
                },
                "status": {
                    "type": "integer",
                    "description": "订单状态: 1待付款 2待接单 3已接单 4派送中 5已完成 6已取消。不传则查全部",
                },
                "page": {"type": "integer", "description": "页码，默认1"},
                "pageSize": {"type": "integer", "description": "每页条数，默认10"},
                "token": {"type": "string", "description": "用户JWT认证令牌（authentication header）"},
            },
        },
        category="order",
        requires_auth=True,
    )
    async def user_order_query(
        order_id: int | None = None,
        status: int | None = None,
        page: int = 1,
        pageSize: int = 10,
        token: str | None = None,
    ) -> str:
        if order_id is not None:
            try:
                detail = await backend_client.get(
                    f"/order/orderDetail/{order_id}", token=token
                )
                return _format_user_order_detail(detail)
            except BackendApiError as e:
                return f"查询订单 #{order_id} 失败：{e}"

        params: dict[str, Any] = {"page": page, "pageSize": pageSize}
        if status is not None:
            params["status"] = status

        try:
            result = await backend_client.get(
                "/order/historyOrders", params=params, token=token
            )
            records = result.get("records", []) if isinstance(result, dict) else []
            return _format_user_orders(records)
        except BackendApiError as e:
            return f"查询订单失败：{e}"

    # ── 2. user_order_action ──
    @server.register(
        name="user_order_action",
        description="用户订单操作：取消订单、催单、再来一单",
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["cancel", "reminder", "repetition"],
                    "description": "操作类型: cancel取消订单 reminder催单 repetition再来一单",
                },
                "order_id": {
                    "type": "integer",
                    "description": "订单ID",
                },
                "token": {"type": "string", "description": "用户JWT认证令牌"},
            },
            "required": ["action", "order_id"],
        },
        category="order",
        requires_auth=True,
    )
    async def user_order_action(
        action: str,
        order_id: int,
        token: str | None = None,
    ) -> str:
        try:
            if action == "cancel":
                await backend_client.put(f"/order/cancel/{order_id}", token=token)
                return f"✅ 订单 #{order_id} 已取消。"

            elif action == "reminder":
                await backend_client.get(f"/order/reminder/{order_id}", token=token)
                return f"✅ 已向商家发送催单提醒，订单 #{order_id}。"

            elif action == "repetition":
                await backend_client.post(f"/order/repetition/{order_id}", token=token)
                return f"✅ 已将订单 #{order_id} 的商品重新加入购物车，您可以返回首页下单。"

            else:
                return f"不支持的操作: {action}。支持的操作: cancel（取消）、reminder（催单）、repetition（再来一单）"

        except BackendAuthError:
            return "操作失败：认证已过期，请重新登录。"
        except BackendApiError as e:
            return f"操作失败：{e}"

    # ── 3. user_menu_query ──
    @server.register(
        name="user_menu_query",
        description="浏览菜单：查询菜品分类、菜品列表、套餐列表",
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
                "token": {"type": "string", "description": "用户JWT认证令牌"},
            },
            "required": ["query_type"],
        },
        category="menu",
        requires_auth=True,
    )
    async def user_menu_query(
        query_type: str,
        category_id: int | None = None,
        token: str | None = None,
    ) -> str:
        try:
            lines: list[str] = []

            if query_type in ("category", "all"):
                try:
                    cats = await backend_client.get(
                        "/category/list", params={"type": 1}, token=token
                    )
                except Exception:
                    cats = []
                if cats:
                    lines.append("📂 菜品分类:")
                    for c in cats:
                        lines.append(f"  - {c.get('name', '?')} (ID: {c.get('id', '?')})")
                    lines.append("")

            if query_type in ("dish", "all"):
                params = {}
                if category_id:
                    params["categoryId"] = category_id
                dishes = await backend_client.get("/dish/list", params=params, token=token)
                dish_list = dishes if isinstance(dishes, list) else dishes.get("records", [])
                lines.append("🍽️ 菜品列表:")
                if dish_list:
                    for d in dish_list:
                        lines.append(f"  - {d.get('name', '?')} | ¥{d.get('price', 0):.2f}")
                else:
                    lines.append("  (暂无菜品)")
                lines.append("")

            if query_type in ("setmeal", "all"):
                setmeals = await backend_client.get("/setmeal/list", params={}, token=token)
                sm_list = setmeals if isinstance(setmeals, list) else setmeals.get("records", [])
                lines.append("📦 套餐列表:")
                if sm_list:
                    for s in sm_list:
                        lines.append(f"  - {s.get('name', '?')} | ¥{s.get('price', 0):.2f}")
                else:
                    lines.append("  (暂无套餐)")

            return "\n".join(lines) if lines else "暂无菜单数据。"

        except BackendApiError as e:
            return f"查询菜单失败：{e}"

    # ── 4. user_shop_info ──
    @server.register(
        name="user_shop_info",
        description="查询店铺信息：营业状态、联系方式、配送费、店铺地址等",
        input_schema={
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "enum": ["status", "merchant", "all"],
                    "description": "查询类型: status营业状态 merchant店铺详情 all全部",
                },
                "token": {"type": "string", "description": "用户JWT认证令牌"},
            },
            "required": ["info_type"],
        },
        category="shop",
        requires_auth=True,
    )
    async def user_shop_info(
        info_type: str,
        token: str | None = None,
    ) -> str:
        try:
            lines: list[str] = []

            if info_type in ("status", "all"):
                from mcp.backend_tools import ORDER_STATUS_MAP, PAY_STATUS_MAP
                status = await backend_client.get("/shop/status", token=token)
                label = "营业中 🟢" if status == 1 else "已打烊 🔴"
                lines.append(f"店铺状态: {label}")

            if info_type in ("merchant", "all"):
                info = await backend_client.get(
                    "/shop/getMerchantInfo", token=token
                )
                shop_name = info.get("shopName", "?") if isinstance(info, dict) else "?"
                phone = info.get("phone", "?") if isinstance(info, dict) else "?"
                address = info.get("shopAddress", "?") if isinstance(info, dict) else "?"
                shop_id = info.get("shopId", "?") if isinstance(info, dict) else "?"
                lines.append(
                    f"店铺名称: {shop_name}\n"
                    f"店铺ID: {shop_id}\n"
                    f"电话: {phone}\n"
                    f"地址: {address}"
                )

            return "\n".join(lines) if lines else "暂无店铺信息。"

        except BackendApiError as e:
            return f"查询店铺信息失败：{e}"

    return server
