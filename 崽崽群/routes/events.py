# -*- coding: utf-8 -*-
"""
崽崽群 SSE 路由 (/events)
线程轮询文件 → asyncio.Queue → SSE 实时推送
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from 崽崽群.state import active_proc

router = APIRouter()

KEEPALIVE_INTERVAL = 15
POLL_INTERVAL = 0.05


@router.get("/events")
async def sse(request: Request):
    """
    SSE 流：
    1. 背景线程轮询 JSONL 文件（跨进程可靠）
    2. 线程把事件放入 asyncio.Queue
    3. SSE 协程从队列读事件，推送给浏览器
    """
    evt_file = [active_proc.get("file")]   # 用列表装着，引用可修改
    read_pos = [0]
    last_ping = [0.0]
    q: asyncio.Queue = asyncio.Queue()
    stop_flag = [False]

    def file_poller():
        """在同步线程中轮询文件，有新内容就放入队列"""
        while not stop_flag[0]:
            now = time.monotonic()
            if now - last_ping[0] >= KEEPALIVE_INTERVAL:
                try:
                    q.put_nowait({"type": "ping", "data": {}})
                except Exception:
                    pass
                last_ping[0] = now

            # 每次轮询都重新读取（/start 可能改变文件路径）
            ef = evt_file[0] or active_proc.get("file")
            if ef and os.path.exists(ef):
                if evt_file[0] is None:
                    evt_file[0] = ef   # 首次发现文件，重置读位置
                    read_pos[0] = 0
                try:
                    size = os.path.getsize(ef)
                    if size > read_pos[0]:
                        with open(ef, "r", encoding="utf-8") as f:
                            f.seek(read_pos[0])
                            new_lines = f.readlines()
                        read_pos[0] = size
                        for line in new_lines:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                                q.put_nowait(obj)
                            except json.JSONDecodeError:
                                q.put_nowait({"type": "message", "data": {"text": line}})
                except PermissionError:
                    pass
                except Exception:
                    pass

            time.sleep(POLL_INTERVAL)

    # 启动文件轮询线程
    poller = threading.Thread(target=file_poller, daemon=True)
    poller.start()

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    obj = await asyncio.wait_for(q.get(), timeout=0.5)
                    etype = obj.get("type", "message")
                    edata = json.dumps(obj.get("data", {}), ensure_ascii=False)
                    yield f"event: {etype}\ndata: {edata}\n\n".encode("utf-8")
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        finally:
            stop_flag[0] = True

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
        },
    )
