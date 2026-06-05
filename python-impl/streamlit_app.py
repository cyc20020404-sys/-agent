from __future__ import annotations

import os
import time
import uuid
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_USER_ID = os.getenv("STREAMLIT_USER_ID", "streamlit-user")

st.set_page_config(page_title="智能客服演示", page_icon="💬", layout="wide")

st.markdown(
    """
    <style>
        .main {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }
        .app-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 20px;
            padding: 20px 24px;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(8px);
        }
        .status-chip {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
            margin-bottom: 6px;
        }
        .status-chip.intent {
            background: #e0e7ff;
            color: #3730a3;
        }
        .status-chip.safe {
            background: #dcfce7;
            color: #166534;
        }
        .status-chip.risk {
            background: #fee2e2;
            color: #991b1b;
        }
        .session-card {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 12px;
        }
        .tiny-muted {
            color: #64748b;
            font-size: 12px;
        }
        .hero-title {
            font-size: 32px;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 4px;
        }
        .hero-subtitle {
            color: #475569;
            font-size: 15px;
            margin-bottom: 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def new_session() -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    return {
        "id": session_id,
        "title": "新会话",
        "messages": [],
        "intent": "unknown",
        "compliance_passed": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


if "sessions" not in st.session_state:
    first_session = new_session()
    st.session_state.sessions = {first_session["id"]: first_session}
    st.session_state.active_session_id = first_session["id"]

if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = API_BASE_URL

if "user_id" not in st.session_state:
    st.session_state.user_id = DEFAULT_USER_ID


def get_active_session() -> dict[str, Any]:
    return st.session_state.sessions[st.session_state.active_session_id]


def build_session_title(first_user_message: str) -> str:
    text = first_user_message.strip().replace("\n", " ")
    return text[:18] + ("..." if len(text) > 18 else "") if text else "新会话"


def switch_session(session_id: str) -> None:
    st.session_state.active_session_id = session_id


def create_session() -> None:
    session = new_session()
    st.session_state.sessions[session["id"]] = session
    st.session_state.active_session_id = session["id"]


def clear_current_session() -> None:
    session = get_active_session()
    session["messages"] = []
    session["title"] = "新会话"
    session["intent"] = "unknown"
    session["compliance_passed"] = True
    session["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def render_status(intent: str, compliance_passed: bool) -> None:
    compliance_class = "safe" if compliance_passed else "risk"
    compliance_text = "合规通过" if compliance_passed else "存在风险"
    st.markdown(
        (
            '<div>'
            f'<span class="status-chip intent">Intent: {intent}</span>'
            f'<span class="status-chip {compliance_class}">{compliance_text}</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_response(text: str, meta_text: str) -> str:
    full_text = text + meta_text
    st.markdown(full_text)
    return full_text


with st.sidebar:
    st.markdown("## 控制台")
    st.text_input("API Base URL", key="api_base_url")
    st.text_input("User ID", key="user_id")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("新建会话", use_container_width=True):
            create_session()
            st.rerun()
    with col_b:
        if st.button("清空聊天", use_container_width=True):
            clear_current_session()
            st.rerun()

    st.markdown("---")
    st.markdown("## 历史会话")

    sessions = list(st.session_state.sessions.values())
    sessions.sort(key=lambda item: item["updated_at"], reverse=True)

    for session in sessions:
        is_active = session["id"] == st.session_state.active_session_id
        label = f"{'● ' if is_active else ''}{session['title']}"
        if st.button(label, key=f"session-{session['id']}", use_container_width=True):
            switch_session(session["id"])
            st.rerun()
        st.markdown(
            f"<div class='tiny-muted'>更新时间：{session['updated_at']}</div>",
            unsafe_allow_html=True,
        )

active_session = get_active_session()

st.markdown(
    """
    <div class="app-card">
        <div class="hero-title">智能客服多 Agent 演示</div>
        <p class="hero-subtitle">一个更接近正式产品形态的前端页面，连接你当前的 FastAPI `/api/chat` 接口。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
render_status(active_session["intent"], active_session["compliance_passed"])
st.caption(f"当前会话 ID：{active_session['id']}")

for message in active_session["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("请输入你的问题")

if prompt:
    if not active_session["messages"]:
        active_session["title"] = build_session_title(prompt)

    user_message = {"role": "user", "content": prompt}
    active_session["messages"].append(user_message)
    active_session["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("正在思考中..."):
            try:
                response = requests.post(
                    f"{st.session_state.api_base_url.rstrip('/')}/api/chat",
                    json={
                        "message": prompt,
                        "user_id": st.session_state.user_id,
                        "session_id": active_session["id"],
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("response", "后端未返回回复内容")
                intent = data.get("intent", "unknown")
                compliance_passed = data.get("compliance_passed", True)
                meta = (
                    "\n\n---\n"
                    f"`intent: {intent}`  "
                    f"`compliance_passed: {compliance_passed}`"
                )
                content = render_response(answer, meta)
                active_session["intent"] = intent
                active_session["compliance_passed"] = compliance_passed
            except requests.RequestException as exc:
                content = f"请求失败：{exc}"
                st.error(content)

    active_session["messages"].append({"role": "assistant", "content": content})
    active_session["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()
