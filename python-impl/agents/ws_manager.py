"""
WebSocket 连接管理器 — 管理 H5 用户端和管理后台之间的实时消息通道

每条升级会话维护两条 WebSocket 连接（user + admin），消息双向透传。
含消息缓冲：一方断开时另一方消息不会丢失，重连后自动回放。
"""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class SessionConnections:
    """一条会话的 WebSocket 连接对 + 消息缓冲"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.user_ws: WebSocket | None = None
        self.admin_ws: WebSocket | None = None
        # 消息缓冲队列：存储 (target, data) 元组
        # target: "admin" | "user"
        self._pending: deque[dict] = deque()

    @property
    def both_connected(self) -> bool:
        return self.user_ws is not None and self.admin_ws is not None

    def buffer(self, data: dict) -> None:
        """消息放入缓冲（目标方断线时）"""
        self._pending.append(data)

    def flush(self) -> list[dict]:
        """取出并清空缓冲"""
        msgs = list(self._pending)
        self._pending.clear()
        return msgs


class WSConnectionManager:
    """全局 WebSocket 连接池"""

    def __init__(self):
        self._sessions: dict[str, SessionConnections] = {}

    def _ensure(self, session_id: str) -> SessionConnections:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionConnections(session_id)
        return self._sessions[session_id]

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def session_count(self) -> int:
        return len(self._sessions)

    # ── register / unregister ──────────────────────────────

    async def connect_user(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        conn = self._ensure(session_id)
        if conn.user_ws:
            try:
                await conn.user_ws.close()
            except Exception:
                pass
        conn.user_ws = ws

        # 告诉管理员用户上线了
        await self._do_send(conn, "admin", {
            "type": "user_connected",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        })

        # 回放缓冲中给用户的积压消息
        for data in conn.flush():
            if data.get("_target") == "user":
                await self._do_send(conn, "user", data)

    async def connect_admin(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        conn = self._ensure(session_id)
        if conn.admin_ws:
            try:
                await conn.admin_ws.close()
            except Exception:
                pass
        conn.admin_ws = ws

        # 回放缓冲中给管理员的积压消息
        for data in conn.flush():
            if data.get("_target") == "admin":
                await self._do_send(conn, "admin", data)

    def disconnect_user(self, session_id: str) -> None:
        conn = self._sessions.get(session_id)
        if conn:
            conn.user_ws = None

    def disconnect_admin(self, session_id: str) -> None:
        conn = self._sessions.get(session_id)
        if conn:
            conn.admin_ws = None

    # ── message routing ────────────────────────────────────

    async def user_to_admin(self, session_id: str, message: str) -> None:
        data = {
            "_target": "admin",
            "type": "user_message",
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
        }
        await self._send_or_buffer(session_id, "admin", data)

    async def admin_to_user(self, session_id: str, message: str, agent_name: str = "") -> None:
        data = {
            "_target": "user",
            "type": "agent_message",
            "role": "agent",
            "content": message,
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat(),
        }
        await self._send_or_buffer(session_id, "user", data)

    async def system_to_user(self, session_id: str, message: str) -> None:
        data = {
            "_target": "user",
            "type": "system_message",
            "role": "system",
            "content": message,
            "timestamp": datetime.now().isoformat(),
        }
        await self._send_or_buffer(session_id, "user", data)

    # ── direct send (no buffering) ─────────────────────────

    async def _send_to_user(self, session_id: str, data: dict) -> None:
        """直接发送任意数据给用户端（不缓冲），用于系统通知"""
        conn = self._sessions.get(session_id)
        if conn:
            await self._do_send(conn, "user", data)

    async def _send_to_admin(self, session_id: str, data: dict) -> None:
        """直接发送任意数据给管理员端（不缓冲），用于系统通知"""
        conn = self._sessions.get(session_id)
        if conn:
            await self._do_send(conn, "admin", data)

    # ── internal ────────────────────────────────────────────

    async def _send_or_buffer(self, session_id: str, target: str, data: dict) -> None:
        """发送消息，如果目标方断线则缓冲"""
        conn = self._sessions.get(session_id)
        if not conn:
            return
        ws = conn.user_ws if target == "user" else conn.admin_ws
        if ws:
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False))
                return
            except Exception:
                if target == "user":
                    conn.user_ws = None
                else:
                    conn.admin_ws = None
        # 目标断线 → 缓冲
        conn.buffer(data)

    async def _do_send(self, conn: SessionConnections, target: str, data: dict) -> None:
        """直接发送（不缓冲），用于系统消息"""
        ws = conn.user_ws if target == "user" else conn.admin_ws
        if ws:
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False))
            except Exception:
                if target == "user":
                    conn.user_ws = None
                else:
                    conn.admin_ws = None


# 全局单例
ws_manager = WSConnectionManager()
