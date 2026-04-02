# -*- coding: utf-8 -*-
"""
崽崽群 配置模块
所有 agent 定义、平台常量、输出清理正则
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

# ── 服务器配置 ────────────────────────────────────────────
PORT = 8766

# HTML 模板路径（启动时由 main.py 动态传入）
HTML_FILE: str | None = None

# ── VM SSH 配置 ──────────────────────────────────────────
VM_SSH = os.environ.get("HERD_VM_SSH", "fayi@172.17.26.221")

# ── 日期常量 ──────────────────────────────────────────────
TODAY     = datetime.now().strftime("%Y%m%d")
TODAY_D   = datetime.now().strftime("%Y年%m月%d日 %H:%M")

# ── Agent 定义 ────────────────────────────────────────────
# platform: "vm" → 通过 SSH 调用 VM 上的 openclaw
# platform: "win" → 通过 PowerShell 调用本机 openclaw
# 新增崽崽只需在 HERD 字典里加一项，平台代码无需改动
HERD: dict[str, dict] = {
    "researcher": {
        "name": "研究崽",
        "color": "#00BCD4",
        "platform": "vm",
        "openclaw_agent": "researcher",
        "think": "深入调研、数据驱动、技术细节扒得深",
    },
    "silijian": {
        "name": "质疑崽",
        "color": "#FFC107",
        "platform": "vm",
        "openclaw_agent": "silijian",
        "think": "找漏洞、泼冷水、识别最容易被忽略的风险",
    },
    "coder": {
        "name": "编码崽",
        "color": "#4CAF50",
        "platform": "vm",
        "openclaw_agent": "coder",
        "think": "代码落地、可行性验证、追求真正能跑",
    },
    "organizer": {
        "name": "整合崽",
        "color": "#9C27B0",
        "platform": "vm",
        "openclaw_agent": "organizer",
        "think": "综合判断、收敛共识、找到最优解",
    },
    # Windows 本地 agent（openclaw agent --agent main --local）
    "assistant": {
        "name": "助手崽",
        "color": "#FF7043",
        "platform": "win",
        "openclaw_agent": "main",
        "think": "从用户的实际需求出发，务实、落地、不空谈",
    },
}

# ── Windows openclaw 输出清理正则 ─────────────────────────
ANSI_RE          = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
# 插件噪音整块（ANSI码前后都去掉）
PLUGIN_BLOCK_RE  = re.compile(
    r"^\x1b\[[0-9;]*m?node\.exe : \[plugins\].*?"
    r"(?:^\x1b\[[0-9;]*m|^\[)(?:plugins|38;5;).*?$",
    re.MULTILINE | re.DOTALL
)
AUTH_WARN_RE     = re.compile(r"^\[agents/model-providers\].*?\n", re.MULTILINE)
PS_ERROR_RE      = re.compile(r"^所在位置.*?\n(?:[+>].*\n)*", re.MULTILINE)
LOCATION_RE      = re.compile(
    r"^(?:所在位置|CategoryInfo|FullyQualifiedErrorId).*?\n",
    re.MULTILINE
)
# 堆栈行 / PowerShell ANSI 行 / 纯ANSI行
PS_LINE_RE       = re.compile(
    r"^\s*(?:\+ |At |CallStack:|CategoryInfo|FullyQualifiedErrorId|"
    r"PowerShell|Node\.exe).*?\n",
    re.MULTILINE
)
PS_ANSI_RE       = re.compile(r"^\s*\x1b\[[0-9;]*m\s*(?:\n|$)", re.MULTILINE)


