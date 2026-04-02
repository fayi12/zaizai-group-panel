# -*- coding: utf-8 -*-
"""
崽崽群 实验路由 (/start)
启动4轮实验子进程
"""
from __future__ import annotations

from fastapi import APIRouter, Form

from 崽崽群.experiments import start_experiment
from 崽崽群.state import state

router = APIRouter()


@router.post("/start")
async def start(question: str = Form("")):
    """
    启动崽崽群实验。

    流程：第1轮并行思考 → 第2轮交叉评论 → 第3轮投票 → 第4轮整合崽综合
    进度通过 SSE /events 实时推送。
    """
    if question:
        state.question = question
    else:
        question = state.question or "崽崽村下一步最值得做什么？"
        state.question = question

    state.reset()
    state.started = True
    start_experiment(question)
    return {"status": "started", "question": question}
