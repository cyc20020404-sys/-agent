"""
短期记忆 — 基于Redis的会话级记忆
存储最近N轮对话上下文，设置TTL自动过期。
适合维护多轮对话的连续性。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


class ShortTermMemory:
    """
    短期记忆：基于Redis的会话缓存。

    特点：
    - Redis存储，支持分布式部署
    - TTL自动过期（默认30分钟）
    - 保留最近N轮对话
    - 支持滑动窗口淘汰
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_turns: int = 20,
        ttl_seconds: int = 1800,
        mysql_store: Any = None,
    ):
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        self._redis_url = redis_url
        self._redis: Any = None
        self._fallback_store: dict[str, list] = {}
        self._mysql_store = mysql_store

    async def _get_redis(self):
        """懒加载Redis连接"""
        if self._redis is None:
            if aioredis is None:
                return None
            try:
                self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def _session_key(self, session_id: str) -> str:
        return f"smartcs:short_term:{session_id}"

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加一条对话消息"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        r = await self._get_redis()

        if r is not None:
            key = self._session_key(session_id)
            await r.rpush(key, json.dumps(message, ensure_ascii=False))
            await r.ltrim(key, -self.max_turns, -1)
            await r.expire(key, self.ttl_seconds)
        else:
            if session_id not in self._fallback_store:
                self._fallback_store[session_id] = []
            self._fallback_store[session_id].append(message)
            if len(self._fallback_store[session_id]) > self.max_turns:
                self._fallback_store[session_id] = self._fallback_store[session_id][-self.max_turns:]

        # 写穿透到 MySQL（静默失败，不影响 Redis 路径）
        if self._mysql_store is not None:
            try:
                await self._mysql_store.add_message(
                    session_id, role, content, message["timestamp"]
                )
            except Exception:
                pass

    async def get_history(self, session_id: str, last_n: int | None = None) -> list[dict]:
        """获取对话历史，Redis 过期后回退 MySQL"""
        r = await self._get_redis()
        n = last_n or self.max_turns

        if r is not None:
            key = self._session_key(session_id)
            raw = await r.lrange(key, -n, -1)
            if raw:
                return [json.loads(item) for item in raw]

            # Redis 为空 → 尝试 MySQL 回退
            if self._mysql_store is not None:
                try:
                    mysql_history = await self._mysql_store.get_messages(session_id, n)
                    if mysql_history:
                        # 回填 Redis，后续读取走缓存
                        for msg in mysql_history:
                            await r.rpush(
                                key, json.dumps(msg, ensure_ascii=False)
                            )
                        await r.ltrim(key, -self.max_turns, -1)
                        await r.expire(key, self.ttl_seconds)
                        return mysql_history
                except Exception:
                    pass
            return []
        else:
            history = self._fallback_store.get(session_id, [])
            if last_n:
                return history[-last_n:]
            return list(history)

    async def clear(self, session_id: str) -> None:
        """清除指定session的短期记忆"""
        r = await self._get_redis()
        if r is not None:
            await r.delete(self._session_key(session_id))
        else:
            self._fallback_store.pop(session_id, None)

    async def get_context_window(self, session_id: str, max_tokens: int = 4000) -> str:
        """获取适配上下文窗口大小的对话历史文本"""
        history = await self.get_history(session_id)

        context_parts = []
        estimated_tokens = 0

        for msg in reversed(history):
            msg_text = f"{msg['role']}: {msg['content']}"
            msg_tokens = len(msg_text) // 2  # 粗略估算
            if estimated_tokens + msg_tokens > max_tokens:
                break
            context_parts.insert(0, msg_text)
            estimated_tokens += msg_tokens

        return "\n".join(context_parts)
