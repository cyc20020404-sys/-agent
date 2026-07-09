"""
人工转接模块 — Human-in-the-Loop 支持
当用户明确请求人工客服时，将对话升级到人工队列，管理后台可接管并回复。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EscalatedSession:
    """一条升级到人工的会话"""
    session_id: str
    user_id: str
    status: str  # "queued" | "active" | "resolved"
    messages: list[dict] = field(default_factory=list)
    agent_id: str = ""
    agent_name: str = ""
    created_at: str = ""
    accepted_at: str = ""
    resolved_at: str = ""
    last_delivered_index: int = 0  # track which agent replies have been delivered to user

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status,
            "message_count": len(self.messages),
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "created_at": self.created_at,
            "accepted_at": self.accepted_at,
            "resolved_at": self.resolved_at,
        }


class HumanHandoffStore:
    """内存中的人工升级会话存储"""

    def __init__(self):
        self._sessions: dict[str, EscalatedSession] = {}

    def escalate(self, session_id: str, user_id: str, messages: list[dict] | None = None) -> EscalatedSession:
        """将某个会话标记为升级到人工；已解决的会话重新激活"""
        existing = self._sessions.get(session_id)
        if existing is not None:
            if existing.status == "resolved":
                # 重新激活已解决的会话
                existing.status = "queued"
                existing.user_id = user_id
                existing.messages = list(messages) if messages else []
                existing.agent_id = ""
                existing.agent_name = ""
                existing.created_at = datetime.now().isoformat()
                existing.accepted_at = ""
                existing.resolved_at = ""
                existing.last_delivered_index = 0
            return existing

        session = EscalatedSession(
            session_id=session_id,
            user_id=user_id,
            status="queued",
            messages=list(messages) if messages else [],
            created_at=datetime.now().isoformat(),
        )
        self._sessions[session_id] = session
        return session

    def list_queued(self) -> list[dict]:
        """获取所有待接管或进行中的会话"""
        return [s.to_dict() for s in self._sessions.values()
                if s.status in ("queued", "active")]

    def list_all(self) -> list[dict]:
        """获取所有升级会话（包括已完成的）"""
        return [s.to_dict() for s in self._sessions.values()]

    def get(self, session_id: str) -> EscalatedSession | None:
        return self._sessions.get(session_id)

    def accept(self, session_id: str, agent_id: str = "admin", agent_name: str = "管理员") -> EscalatedSession | None:
        """管理员接管会话"""
        session = self._sessions.get(session_id)
        if session:
            session.status = "active"
            session.agent_id = agent_id
            session.agent_name = agent_name
            session.accepted_at = datetime.now().isoformat()
        return session

    def agent_reply(self, session_id: str, message: str) -> EscalatedSession | None:
        """管理员回复消息"""
        session = self._sessions.get(session_id)
        if session:
            session.messages.append({
                "role": "agent",
                "content": message,
                "timestamp": datetime.now().isoformat(),
            })
        return session

    def user_message(self, session_id: str, message: str) -> EscalatedSession | None:
        """用户发来的新消息（追加到会话）"""
        session = self._sessions.get(session_id)
        if session and session.status == "active":
            session.messages.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat(),
            })
        return session

    def get_messages(self, session_id: str, since_index: int = 0) -> list[dict]:
        """获取会话消息（管理员端轮询用）"""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session.messages[since_index:]

    def resolve(self, session_id: str) -> EscalatedSession | None:
        """标记会话为已解决"""
        session = self._sessions.get(session_id)
        if session:
            session.status = "resolved"
            session.resolved_at = datetime.now().isoformat()
        return session

    def get_undelivered_agent_replies(self, session_id: str) -> list[str]:
        """获取用户尚未收到的人工回复，并标记为已投递"""
        session = self._sessions.get(session_id)
        if not session:
            return []
        undelivered = []
        for i, msg in enumerate(session.messages):
            if i >= session.last_delivered_index and msg.get("role") == "agent":
                undelivered.append(msg["content"])
        session.last_delivered_index = len(session.messages)
        return undelivered

    def is_escalated(self, session_id: str) -> bool:
        """检查一个会话是否已升级到人工（不包含已解决的会话）"""
        session = self._sessions.get(session_id)
        return session is not None and session.status != "resolved"


HUMAN_HANDOFF_SYSTEM_PROMPT = """你是一个外卖客服系统的人工转接处理模块。
当用户明确要求人工服务时，你需要：
1. 确认用户需要人工客服
2. 告知用户已为其转接人工客服，请耐心等待
3. 告知预计等待时间（根据情况给一个合理估计，如3-5分钟）
4. 不要承诺具体回复时间，保持友好专业

请直接输出给用户的回复，语气友好。"""
