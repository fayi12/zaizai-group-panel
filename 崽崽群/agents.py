# -*- coding: utf-8 -*-
"""
崽崽群 Agent 调度器
根据 agent 配置的平台字段，分发到对应的 runner
"""
from __future__ import annotations

from 崽崽群.config import HERD
from 崽崽群.runners import run_vm, run_win
from 崽崽群.runners.vm import msg_to_vm, cleanup_vm


def openclaw_run(agent_id: str, msg_text: str, thinking: str = "high", timeout: int = 600) -> str:
    """
    统一调用接口，根据 agent 所在平台分发。

    Args:
        agent_id: HERD 中的 agent key
        msg_text: 要发给 agent 的消息
        thinking: 思考深度 ("high" | "medium" | "low")
        timeout: 超时秒数

    Returns:
        agent 的原始回复文本（不含噪音，已在 runner 层清理）
    """
    info = HERD.get(agent_id, {})
    platform = info.get("platform", "vm")

    if platform == "win":
        return run_win(msg_text, thinking=thinking, timeout=timeout)

    # VM 平台：消息写入临时文件，通过 SSH 传递给 openclaw
    openclaw_agent = info.get("openclaw_agent", agent_id)
    vm_path = msg_to_vm(msg_text)
    try:
        cmd = (
            f"openclaw agent --agent {openclaw_agent} --local "
            f"--session-id isolated --thinking {thinking} "
            f"--message \"$(cat {vm_path})\""
        )
        return run_vm(cmd, timeout=timeout)
    finally:
        cleanup_vm(vm_path)
