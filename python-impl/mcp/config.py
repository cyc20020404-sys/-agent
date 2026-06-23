"""
MCP 后端配置 — 从环境变量读取 Spring Boot 后端地址
"""
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8080/admin")
BACKEND_TOKEN_HEADER = os.getenv("BACKEND_TOKEN_HEADER", "token")
BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "15"))
