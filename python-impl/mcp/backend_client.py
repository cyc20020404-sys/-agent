"""
Spring Boot 后端 HTTP 客户端 — 统一封装 Result<T> 解包、JWT 透传、错误处理
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from mcp.config import BACKEND_BASE_URL, BACKEND_TOKEN_HEADER, BACKEND_TIMEOUT

logger = logging.getLogger(__name__)


class BackendApiError(Exception):
    """后端 API 返回的错误"""

    def __init__(self, message: str, code: int = 0, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class BackendAuthError(BackendApiError):
    """鉴权失败（401）"""

    pass


class BackendClient:
    """
    Spring Boot 后端 HTTP 客户端。

    封装了：
    - Result<T> 统一响应解包 (code/msg/data)
    - JWT token 透传
    - 超时和错误处理
    - 401 专用异常
    """

    def __init__(self, base_url: str = BACKEND_BASE_URL, header_name: str = BACKEND_TOKEN_HEADER):
        self.base_url = base_url.rstrip("/")
        self.header_name = header_name

    # ── 请求头构建 ──

    def _headers(self, token: str | None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if token:
            headers[self.header_name] = token
        return headers

    # ── 响应解包 ──

    def _unwrap_result(self, resp_json: dict) -> Any:
        """将 Spring Boot Result<T> 解包为纯 data"""
        code = resp_json.get("code")
        if code != 1:
            msg = resp_json.get("msg") or "后端返回未知错误"
            raise BackendApiError(msg, code=code)
        return resp_json.get("data")

    # ── HTTP 方法 ──

    async def get(
        self,
        path: str,
        params: dict | None = None,
        token: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=self._headers(token))
        except httpx.TimeoutException:
            raise BackendApiError(f"后端请求超时: GET {url}")
        except httpx.ConnectError:
            raise BackendApiError(f"无法连接后端服务: {url}")

        if resp.status_code == 401:
            raise BackendAuthError("认证已过期，请重新登录", status_code=401)

        if resp.status_code >= 400:
            raise BackendApiError(
                f"后端返回 HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        return self._unwrap_result(resp.json())

    async def put(
        self,
        path: str,
        body: dict | None = None,
        token: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT) as client:
                resp = await client.put(
                    url, json=body or {}, headers=self._headers(token)
                )
        except httpx.TimeoutException:
            raise BackendApiError(f"后端请求超时: PUT {url}")
        except httpx.ConnectError:
            raise BackendApiError(f"无法连接后端服务: {url}")

        if resp.status_code == 401:
            raise BackendAuthError("认证已过期，请重新登录", status_code=401)

        if resp.status_code >= 400:
            raise BackendApiError(
                f"后端返回 HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        return self._unwrap_result(resp.json())

    async def post(
        self,
        path: str,
        body: dict | None = None,
        token: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT) as client:
                resp = await client.post(
                    url, json=body or {}, headers=self._headers(token)
                )
        except httpx.TimeoutException:
            raise BackendApiError(f"后端请求超时: POST {url}")
        except httpx.ConnectError:
            raise BackendApiError(f"无法连接后端服务: {url}")

        if resp.status_code == 401:
            raise BackendAuthError("认证已过期，请重新登录", status_code=401)

        if resp.status_code >= 400:
            raise BackendApiError(
                f"后端返回 HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        return self._unwrap_result(resp.json())
