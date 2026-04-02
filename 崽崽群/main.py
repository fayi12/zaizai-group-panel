# -*- coding: utf-8 -*-
"""
崽崽群 FastAPI 主应用
注册所有路由，提供 HTML 面板
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 将崽崽群包路径加入 sys.path（支持 python main.py 直接运行）
_ROOT = Path(__file__).resolve().parent          # 崽崽群/
_PARENT = _ROOT.parent                            # gstack/
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))            # 让 "import 崽崽群" 能找到崽崽群/

import 崽崽群.config as cfg
from 崽崽群.config import PORT
from 崽崽群.state import state

# 动态设置 HTML_FILE（main.py 同级 templates/index.html）
cfg.HTML_FILE = str(_ROOT / "templates" / "index.html")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from 崽崽群.routes import chat, events, exp, state as state_route

app = FastAPI(title="崽崽群实时面板", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 注册路由
app.include_router(events.router,   tags=["events"])
app.include_router(chat.router,     tags=["chat"])
app.include_router(exp.router,       tags=["experiment"])
app.include_router(state_route.router, tags=["state"])


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(cfg.HTML_FILE, media_type="text/html; charset=utf-8")


# ── 子进程入口（--run-subprocess）────────────────────────
if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="崽崽群实时面板")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("-q", "--question", dest="question", default="")
    parser.add_argument("--run-subprocess", dest="subprocess_question", default=None)
    parser.add_argument("--evtfile", dest="evt_file", default=None)
    args = parser.parse_args()

    if args.subprocess_question and args.evt_file:
        # 子进程模式：直接运行实验逻辑
        from 崽崽群.experiments import subprocess_main
        subprocess_main(args.subprocess_question, args.evt_file)
    elif args.subprocess_question:
        from 崽崽群.experiments import subprocess_main
        import tempfile
        subprocess_main(args.subprocess_question, tempfile.mktemp(suffix=".jsonl"))
    else:
        # Web 服务模式
        print(f"\n  崽崽群实时面板 v2.0\n  浏览器打开: http://localhost:{args.port}\n")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=args.port,
            log_level="warning",
            # 兼容 Windows
            loop="asyncio" if sys.platform == "win32" else "auto",
        )
