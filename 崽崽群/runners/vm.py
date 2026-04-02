# -*- coding: utf-8 -*-
"""
崽崽群 VM Runner
通过 SSH 调用远程 Linux VM 上的 openclaw agent
"""
from __future__ import annotations

import os
import platform
import subprocess
import uuid
from pathlib import Path

from 崽崽群.config import VM_SSH, ANSI_RE, PLUGIN_BLOCK_RE, AUTH_WARN_RE

IS_WIN = platform.system() == "Windows"


def msg_to_vm(msg_text: str) -> str:
    """
    把消息写入 VM 上的临时文件。
    末尾换行符会被去掉，避免 ``$(cat file)`` 传递给 shell 时截断命令。
    """
    fid = uuid.uuid4().hex[:8]
    vm_path = f"/tmp/herd_msg_{fid}.txt"
    clean = msg_text.rstrip("\r\n")

    if IS_WIN:
        local = Path(os.environ["TEMP"]) / f"herd_msg_{fid}.txt"
        local.write_text(clean, encoding="utf-8")
        subprocess.run(
            ["scp", "-T", str(local), f"{VM_SSH}:{vm_path}"],
            timeout=30, capture_output=True,
            encoding="utf-8", errors="replace",
        )
        local.unlink(missing_ok=True)
    else:
        Path(vm_path).write_text(clean, encoding="utf-8")

    return vm_path


def cleanup_vm(vm_path: str) -> None:
    """删除 VM 上的临时消息文件"""
    try:
        if IS_WIN:
            subprocess.run(
                ["ssh", VM_SSH, f"rm -f {vm_path}"],
                timeout=10, capture_output=True,
            )
        else:
            subprocess.run(
                f"rm -f {vm_path}",
                shell=True, timeout=10, capture_output=True,
            )
    except Exception:
        pass


def _clean_vm_output(text: str) -> str:
    """去掉 VM openclaw 输出的启动噪音，只留实际回复。"""
    text = ANSI_RE.sub("", text)
    text = PLUGIN_BLOCK_RE.sub("", text)
    text = AUTH_WARN_RE.sub("", text)
    text = text.strip()
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts[-1] if parts else text


def run_vm(cmd: str, timeout: int = 600) -> str:
    """
    在 VM 上执行命令，结果写入 UTF-8 文件后读取。
    用文件中转而非 stdout 管道，绕过 Windows SSH 客户端的 cp936 控制台编码问题。
    """
    fid = uuid.uuid4().hex[:8]
    out_path = f"/tmp/herd_out_{fid}.txt"

    # 把命令输出重定向到 VM 上的文件，再用 scp 拉回来
    escaped_cmd = cmd.replace('"', '\\"')
    ssh_cmd = f'sh -c \'exec {cmd} > {out_path} 2>&1\' '

    if IS_WIN:
        r = subprocess.run(
            ["ssh", "-T", VM_SSH, ssh_cmd],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        # SCP 拉回输出文件（用 -q 安静模式）
        local = Path(os.environ["TEMP"]) / f"herd_out_{fid}.txt"
        subprocess.run(
            ["scp", "-T", "-q", f"{VM_SSH}:{out_path}", str(local)],
            timeout=30, capture_output=True,
            encoding="utf-8", errors="replace",
        )
        try:
            text = local.read_text(encoding="utf-8")
            local.unlink(missing_ok=True)
        except Exception:
            text = ""
        # 顺手清理 VM 上的文件
        subprocess.run(
            ["ssh", VM_SSH, f"rm -f {out_path}"],
            timeout=10, capture_output=True,
        )
    else:
        text = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        ).stdout or ""

    return _clean_vm_output(text.strip())
