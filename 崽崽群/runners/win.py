# -*- coding: utf-8 -*-
"""
崽崽群 Windows Runner
通过 PowerShell + Base64 调用本机 openclaw agent
"""
from __future__ import annotations

import base64
import os
import subprocess
import uuid
from pathlib import Path

import 崽崽群.config as cfg


def clean_win_output(text: str) -> str:
    """
    去掉 Windows openclaw 输出的启动噪音，只留实际回复。

    处理顺序：
    1. ANSI 颜色码 → 2. 插件噪音整块 → 3. auth/powershell 噪音行
    → 4. 纯ANSI码行 → 5. 取最后段落
    """
    text = cfg.ANSI_RE.sub("", text)
    text = cfg.PLUGIN_BLOCK_RE.sub("", text)
    text = cfg.AUTH_WARN_RE.sub("", text)
    text = cfg.PS_ERROR_RE.sub("", text)
    text = cfg.LOCATION_RE.sub("", text)
    text = cfg.PS_LINE_RE.sub("", text)
    text = cfg.PS_ANSI_RE.sub("", text)
    text = text.strip()
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts[-1] if parts else text


def run_win(msg_text: str, thinking: str = "high", timeout: int = 600) -> str:
    """
    在 Windows 上通过 PowerShell 调用 openclaw agent。

    消息通过 Base64 传递（避免 PowerShell 编码问题），
    openclaw 输出重定向到 UTF-8 文件后再读取。
    """
    tmp_out = Path(os.environ["TEMP"]) / f"claude_out_{uuid.uuid4().hex[:8]}.txt"
    tmp_ps1 = Path(os.environ["TEMP"]) / f"claude_{uuid.uuid4().hex[:8]}.ps1"

    # Base64 编码本身会去掉末尾空白
    msg_b64 = base64.b64encode(msg_text.encode("utf-8")).decode("ascii")

    ps1 = (
        "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
        "chcp 65001 > $null\n"
        f"$msg = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{msg_b64}'))\n"
        f"openclaw agent --agent main --local --session-id isolated "
        f"--thinking {thinking} --message $msg 2>&1 | Out-File -FilePath '{tmp_out}' -Encoding UTF8\n"
    )
    tmp_ps1.write_text(ps1, encoding="utf-8", newline="\n")

    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-File", str(tmp_ps1)]

    try:
        subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        tmp_ps1.unlink(missing_ok=True)

        if tmp_out.exists():
            raw = tmp_out.read_bytes()
            tmp_out.unlink(missing_ok=True)
            try:
                text = raw.decode("utf-8", errors="replace").strip()
            except Exception:
                text = raw.decode("gbk", errors="replace").strip()
            return clean_win_output(text)
        return "[无输出]"

    except subprocess.TimeoutExpired:
        tmp_ps1.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)
        return "[超时]"
    except Exception as ex:
        tmp_ps1.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)
        return f"[错误: {ex}]"
