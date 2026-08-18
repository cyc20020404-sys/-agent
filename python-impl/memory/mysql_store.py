"""
MySQL 持久化存储 — 聊天记录写穿透 + 历史查询

与 ShortTermMemory 配合使用：
- add_message：每写入一条消息就同时写入 MySQL（写穿透）
- get_messages：Redis 过期后从 MySQL 回读，并回填 Redis
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MysqlStore:
    """异步 MySQL 连接池，管理 chat_history 表的读写"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "sky_take_out",
        user: str = "root",
        password: str = "",
        pool_size: int = 5,
        pool_recycle: int = 3600,
    ):
        self._config = {
            "host": host,
            "port": port,
            "db": database,
            "user": user,
            "password": password,
            "minsize": 1,
            "maxsize": pool_size,
            "pool_recycle": pool_recycle,
            "autocommit": True,
            "charset": "utf8mb4",
        }
        self._pool: Any = None

    async def _get_pool(self):
        """懒初始化连接池。MySQL 不可用时返回 None"""
        if self._pool is not None:
            return self._pool

        try:
            import aiomysql
            self._pool = await aiomysql.create_pool(**self._config)
            await self._ensure_table()
            logger.info("MySQL 连接池已创建，chat_history 表就绪")
        except Exception as e:
            logger.warning(f"MySQL 连接失败，聊天记录不会持久化: {e}")
            self._pool = None
        return self._pool

    async def _ensure_table(self) -> None:
        """确保 chat_history 表存在"""
        pool = self._pool
        if pool is None:
            return
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id          BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        session_id  VARCHAR(128)    NOT NULL,
                        role        VARCHAR(20)     NOT NULL,
                        content     TEXT            NOT NULL,
                        ts          DATETIME(3)     NOT NULL,
                        INDEX idx_session (session_id),
                        INDEX idx_session_ts (session_id, ts)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

    async def add_message(
        self, session_id: str, role: str, content: str, timestamp: str
    ) -> None:
        """插入一条聊天消息（静默失败）"""
        pool = await self._get_pool()
        if pool is None:
            return
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO chat_history (session_id, role, content, ts) "
                        "VALUES (%s, %s, %s, %s)",
                        (session_id, role, content, timestamp),
                    )
        except Exception as e:
            logger.warning(f"MySQL 写入消息失败 (session={session_id}): {e}")

    async def get_messages(
        self, session_id: str, last_n: int | None = None
    ) -> list[dict]:
        """按时间顺序查询消息，返回 {role, content, timestamp} 列表"""
        pool = await self._get_pool()
        if pool is None:
            return []
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    limit = f"LIMIT {last_n}" if last_n else ""
                    await cur.execute(
                        f"SELECT role, content, ts FROM chat_history "
                        f"WHERE session_id = %s ORDER BY ts ASC {limit}",
                        (session_id,),
                    )
                    rows = await cur.fetchall()
                    return [
                        {"role": r[0], "content": r[1], "timestamp": str(r[2])}
                        for r in rows
                    ]
        except Exception as e:
            logger.warning(f"MySQL 查询历史失败 (session={session_id}): {e}")
            return []

    async def close(self) -> None:
        """关闭连接池（优雅退出时调用）"""
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("MySQL 连接池已关闭")
