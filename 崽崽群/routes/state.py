# -*- coding: utf-8 -*-
"""
崽崽群 状态路由 (/state)
从 JSONL 文件重建状态，用于页面刷新恢复
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter

from 崽崽群.state import active_proc, state

router = APIRouter()


@router.get("/state")
async def get_state():
    """
    返回当前完整状态（用于页面刷新后恢复）。
    优先从 JSONL 文件重建实验进度，辅以内存 state。
    """
    evt_file = active_proc.get("file")
    phase = "idle"
    r1, r2, votes_total, report_text = {}, {}, {}, ""

    if evt_file and os.path.exists(evt_file):
        try:
            with open(evt_file, "r", encoding="utf-8") as ef:
                for line in ef:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        t = obj.get("type", "")
                        d = obj.get("data", {})
                        if t == "phase_change":
                            phase = d.get("phase", "idle")
                        elif t == "answer":
                            r1[d.get("agent_id", "")] = d.get("text", "")
                        elif t == "comment":
                            r2[d.get("agent_id", "")] = d.get("text", "")
                        elif t == "vote_complete":
                            votes_total = d.get("votes", {})
                        elif t == "experiment_complete":
                            votes_total = d.get("votes", {})
                            report_text = d.get("report", "")
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    with state.lock:
        state.phase = phase
        state.r1 = r1
        state.r2 = r2
        state.votes = {"total": votes_total, "by_voter": {}}
        state.report = report_text
        return {
            "phase": state.phase,
            "question": state.question,
            "started": state.started,
            "r1": state.r1,
            "r2": state.r2,
            "votes": state.votes,
            "report": state.report,
            "chat_history": list(state.chat_history),
            "thinking": dict(state.thinking),
        }
