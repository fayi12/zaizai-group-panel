# -*- coding: utf-8 -*-
"""
崽崽群 聊天路由 (/chat)
支持自由聊天和 @提及（@all 或 @agent_id）
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form

from 崽崽群.agents import openclaw_run
from 崽崽群.config import HERD
from 崽崽群.state import active_proc, state

router = APIRouter()


def emit_evt(etype: str, data: dict) -> None:
    """向 SSE 推送事件：写 JSONL 文件 → 文件轮询线程读取 → SSE 流"""
    obj = {"type": etype, "data": data}

    # 获取活跃的事件文件（实验用，或新建临时文件供聊天用）
    evt_file = active_proc.get("file")
    if not evt_file:
        evt_file = tempfile.mktemp(suffix=".jsonl")
        Path(evt_file).touch()
        active_proc["file"] = evt_file

    # 写 JSONL 文件 → 文件轮询线程 → SSE 推送
    try:
        with open(evt_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass


def run_agent_chat(agent_id: str, msg_text: str, thinking: str = "high", timeout: int = 600) -> str:
    """运行单个崽崽，直接返回结果"""
    result = openclaw_run(agent_id, msg_text, thinking=thinking, timeout=timeout)
    return result or "[无响应]"


@router.post("/chat")
async def chat(
    agents: str = Form(""),
    message: str = Form(""),
    mentions: str = Form(""),
):
    """
    自由聊天。

    参数:
        agents: 逗号分隔的 agent_id，如 "researcher,silijian"
        message: 用户消息（支持 @agent_id 格式）
        mentions: 额外指定的 agent_id（前端 @提及解析后传入）

    @提及行为：
        - 消息中含 @researcher → researcher 自动加入回复列表
        - @all → 所有 HERD 中的崽崽加入回复列表
    """
    if not agents and not mentions:
        return {"status": "ok", "agents": [], "message": message}

    agent_list = {a.strip() for a in agents.split(",") if a.strip() in HERD}

    # 解析消息中的 @提及
    if message:
        import re
        for m in re.finditer(r"@(\w+)", message):
            mentioned = m.group(1)
            if mentioned == "all":
                agent_list.update(HERD.keys())
            elif mentioned in HERD:
                agent_list.add(mentioned)

    if not agent_list:
        return {"status": "error", "reason": "没有有效的崽"}

    agent_list = sorted(agent_list)

    now = datetime.now().strftime("%H:%M:%S")

    # 写入用户消息
    with state.lock:
        state.chat_history.append({"from": "user", "text": message, "time": now})
    emit_evt("user_message", {"text": message, "time": now})

    # 并行执行（使用全局 AGENT_POOL，最多2并发）
    from 崽崽群.state import AGENT_POOL

    def handle_agent(aid: str) -> None:
        info = HERD.get(aid, {})
        emit_evt("thinking", {
            "text": f"{info.get('name', aid)} 正在思考...",
            "agent_id": aid,
            "agent_name": info.get("name", aid),
            "color": info.get("color", "#888"),
        })
        with state.lock:
            state.thinking[aid] = True

        result = run_agent_chat(aid, message, thinking="high", timeout=600)

        with state.lock:
            state.thinking.pop(aid, None)
            state.chat_history.append({
                "from": aid, "text": result,
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent_name": info.get("name", aid),
                "color": info.get("color", "#888"),
            })

        emit_evt("agent_response", {
            "text": result,
            "agent_id": aid,
            "agent_name": info.get("name", aid),
            "color": info.get("color", "#888"),
            "time": datetime.now().strftime("%H:%M:%S"),
        })

    futures = [AGENT_POOL.submit(handle_agent, aid) for aid in agent_list]
    for fut in futures:
        fut.result()

    return {"status": "ok", "agents": agent_list, "message": message}
