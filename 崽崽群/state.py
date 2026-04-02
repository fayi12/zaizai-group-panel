# -*- coding: utf-8 -*-
"""
崽崽群 状态管理模块
State 类（线程安全）+ 活跃实验进程 + 全局线程池 + SSE 事件队列
"""
from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# ── 全局线程池（所有 agent 调用共享，限制最多 2 并发避免卡顿）───
AGENT_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agent-")

# ── SSE 实时事件队列（替代文件轮询，保证实时推送）──────────────
# 写入端：emit_evt() 从 ThreadPool 线程 put_nowait()
# 读取端：SSE endpoint  await event_q.get()
event_q: asyncio.Queue = asyncio.Queue()

# ── 活跃实验进程 ──────────────────────────────────────────
active_proc: dict[str, Any] = {
    "proc": None,   # subprocess.Popen 对象
    "file": None,   # JSONL 事件文件路径（仅用于 /state 恢复历史）
}

# ── 应用状态（线程安全）────────────────────────────────────
class State:
    """线程安全的崽崽群全局状态"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.phase: str = "idle"
        self.question: str = ""
        self.started: bool = False
        # 实验中间结果
        self.r1: dict[str, str] = {}      # Round1 答案
        self.r2: dict[str, str] = {}      # Round2 评论
        self.votes: dict[str, Any] = {"total": {}, "by_voter": {}}
        self.report: str = ""
        # 聊天历史（所有模式共用）
        self.chat_history: list[dict] = []
        # 正在思考的 agent
        self.thinking: dict[str, bool] = {}

    def reset(self) -> None:
        with self.lock:
            self.phase = "idle"
            self.started = False
            self.r1.clear()
            self.r2.clear()
            self.votes = {"total": {}, "by_voter": {}}
            self.report = ""

    def to_dict(self) -> dict:
        with self.lock:
            return {
                "phase": self.phase,
                "question": self.question,
                "started": self.started,
                "chat_history": list(self.chat_history),
                "thinking": dict(self.thinking),
                "active_proc": bool(active_proc["proc"]),
            }


# 全局单例
state = State()
