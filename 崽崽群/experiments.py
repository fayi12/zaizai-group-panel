# -*- coding: utf-8 -*-
"""
崽崽群 实验逻辑模块
包含：emit() JSONL写入、run_experiment_file() 4轮实验、start_experiment() 进程启动
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import TextIO

from 崽崽群.agents import openclaw_run
from 崽崽群.config import HERD, TODAY_D
from 崽崽群.state import active_proc, AGENT_POOL, event_q

# ── JSONL 事件写入 ────────────────────────────────────────

def emit(f: TextIO, etype: str, data: dict) -> None:
    """向 JSONL 文件写入（供 SSE 推送）+ 尝试写入队列（仅对本进程有效）"""
    obj = {"type": etype, "data": data}
    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    f.flush()
    try:
        event_q.put_nowait(obj)
    except Exception:
        pass


# ── 实验四轮逻辑 ──────────────────────────────────────────

def run_experiment_file(question: str, out_path: str) -> None:
    """
    实验主逻辑，按轮次执行，结果写入 JSONL 文件。

    第1轮 并行思考（最多2并发）
    第2轮 交叉评论（串行）
    第3轮 投票（串行）
    第4轮 整合崽综合（仅organizer）
    """
    f: TextIO = open(out_path, "w", encoding="utf-8", buffering=1)
    try:
        def e(etype: str, data: dict) -> None:
            emit(f, etype, data)

        e("phase_change", {
            "phase": "round1", "name": "第1轮：并行思考",
            "text": f"第1轮：{len(HERD)}崽崽同时开始思考"
        })

        # ── 第1轮：并行思考 ─────────────────────────────
        results: dict[str, str] = {}

        def think(aid: str, info: dict) -> None:
            msg = (
                f"【问题】{question}\n\n"
                f"直接输出你的答案（200-400字）：\n"
                f"1. 你的核心判断是什么\n"
                f"2. 支撑判断的关键证据\n"
                f"3. 最容易被忽略的一点\n\n"
                f"不要标题，不要客套，直接说。"
            )
            e("thinking", {"text": f"{info['name']} 正在思考...", "agent_id": aid})
            f.flush()
            try:
                r = openclaw_run(aid, msg, thinking="high", timeout=900)
            except Exception as ex:
                r = f"[{aid} 调用失败: {ex}]"
            r = r or "[无输出]"
            results[aid] = r
            e("answer", {
                "text": r, "agent_id": aid, "agent_name": info["name"],
                "color": info["color"], "time": datetime.now().strftime("%H:%M:%S"),
            })
            e("answer_complete", {"agent_id": aid})
            f.flush()

        # 使用全局共享线程池（max_workers=2）
        futures = [AGENT_POOL.submit(think, aid, info) for aid, info in HERD.items()]
        for fut in futures:
            fut.result()

        # ── 第2轮：交叉评论 ─────────────────────────────
        e("phase_change", {
            "phase": "round2", "name": "第2轮：交叉评论",
            "text": "第2轮：崽崽们互相阅读答案并评论"
        })
        comments: dict[str, str] = {}
        for aid, info in HERD.items():
            others = "\n\n".join(
                f"【{HERD[a]['name']}】\n{results.get(a, '')[:400]}"
                for a in HERD if a != aid
            )
            msg = (
                f"【问题】{question}\n\n"
                f"【其他崽崽的答案】\n{others}\n\n"
                f"输出你的评论：\n"
                f"## 你认同的观点\n"
                f"## 你认为的问题\n"
                f"## 你的补充或反对\n\n"
                f"直接输出评论内容。"
            )
            e("thinking", {"text": f"{info['name']} 正在阅读其他崽崽的答案...", "agent_id": aid})
            f.flush()
            try:
                r = openclaw_run(aid, msg, thinking="high", timeout=600)
            except Exception as ex:
                r = f"[{aid} 评论失败: {ex}]"
            r = r or "[无评论]"
            comments[aid] = r
            e("comment", {
                "text": r, "agent_id": aid, "agent_name": info["name"],
                "color": info["color"], "time": datetime.now().strftime("%H:%M:%S"),
            })
            f.flush()
            time.sleep(1)

        # ── 第3轮：投票 ────────────────────────────────
        e("phase_change", {
            "phase": "round3", "name": "第3轮：投票",
            "text": "第3轮：崽崽们互相投票打分"
        })
        total: dict[str, int] = {a: 0 for a in HERD}
        for vid, info in HERD.items():
            sums = "\n".join(
                f"【{HERD[a]['name']}】{results.get(a, '')[:200]}"
                for a in HERD
            )
            msg = (
                f"【问题】{question}\n\n"
                f"【各崽崽的答案摘要】\n{sums}\n\n"
                f"只输出以下格式（严格按格式）：\n"
                f"VOTE:\nresearcher: +1\nsilijian: -1\ncoder: +1\norganizer: 0"
            )
            try:
                raw = openclaw_run(vid, msg, thinking="high", timeout=300) or ""
            except Exception as ex:
                raw = f"[{vid} 投票失败: {ex}]"
            parsed: dict[str, int] = {}
            import re as re_module
            for line in raw.splitlines():
                m = re_module.match(
                    r"(researcher|silijian|coder|organizer|assistant)\s*[:=]\s*([+-]?\d)",
                    line,
                )
                if m:
                    parsed[m.group(1)] = int(m.group(2))
            for a, s in parsed.items():
                if a in total:
                    total[a] += s
            e("vote", {
                "text": f"投票: {raw[:80]}", "agent_id": vid, "agent_name": info["name"],
                "color": info["color"], "time": datetime.now().strftime("%H:%M:%S"),
            })
            f.flush()
            time.sleep(0.5)

        e("vote_complete", {"votes": total})

        # ── 第4轮：整合崽综合 ───────────────────────────
        e("phase_change", {
            "phase": "round4", "name": "第4轮：整合崽综合",
            "text": "第4轮：整合崽综合最终报告"
        })
        answers = "\n\n".join(f"=== {HERD[a]['name']} ===\n{results.get(a, '')}" for a in HERD)
        cmts = "\n\n".join(f"=== {HERD[a]['name']} 评论 ===\n{comments.get(a, '')}" for a in HERD)
        ranking = "\n".join(
            f"  {HERD[a]['name']}：{s:+d}票"
            for a, s in sorted(total.items(), key=lambda x: -x[1])
        )
        msg = (
            f"你是整合崽，崽崽群讨论的主持人。\n\n"
            f"【原始问题】{question}\n\n"
            f"【各崽崽的答案】\n{answers}\n\n"
            f"【各崽崽的评论】\n{cmts}\n\n"
            f"【投票结果】\n{ranking}\n\n"
            f"输出崽崽群最终报告（直接输出，不要废话）：\n\n"
            f"# 崽崽群最终报告 {TODAY_D}\n\n"
            f"## 核心结论\n（1-3句话，明确判断）\n\n"
            f"## 最有价值的观点\n（来自谁，什么观点，为什么有价值，3条）\n\n"
            f"## 被否决的观点\n（谁的答案哪里有问题）\n\n"
            f"## 涌现的新洞察\n（多崽讨论中，单个崽没想到的新发现）\n\n"
            f"## 下一步行动\n（1-3个具体可执行的步骤）"
        )
        e("thinking", {"text": "整合崽 正在综合所有崽崽的讨论...", "agent_id": "organizer"})
        f.flush()
        try:
            report = openclaw_run("organizer", msg, thinking="high", timeout=600) or "[无报告]"
        except Exception as ex:
            report = f"[整合崽 综合失败: {ex}]"
        e("final_report", {
            "text": report, "agent_id": "organizer", "agent_name": "整合崽",
            "color": HERD["organizer"]["color"],
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        e("experiment_complete", {
            "votes": total, "report": report,
            "results": results, "comments": comments,
        })
        f.flush()

    except Exception as ex:
        import traceback
        e("error", {"text": str(ex), "trace": traceback.format_exc()})
    finally:
        f.close()


# ── 子进程入口 ────────────────────────────────────────────

def subprocess_main(question: str, evt_file: str) -> None:
    """--run-subprocess 入口：直接运行实验逻辑"""
    run_experiment_file(question, evt_file)


def start_experiment(question: str) -> str:
    """
    启动实验子进程，返回 JSONL 事件文件路径。
    主进程通过轮询该文件向浏览器推送 SSE 事件。
    """
    proc = active_proc["proc"]
    if proc:
        try:
            proc.terminate()
        except Exception:
            pass

    evt_file = tempfile.mktemp(suffix=".jsonl")
    Path(evt_file).touch()
    active_proc["file"] = evt_file

    script = Path(__file__).resolve().parent / "main.py"
    # 用干净的环境（只含 ASCII key）避免 Windows CJK 用户环境导致子进程路径乱码
    clean_env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    for k, v in os.environ.items():
        try:
            str(k); str(v)
            clean_env[k] = v
        except Exception:
            pass

    proc = subprocess.Popen(
        [sys.executable, str(script), "--run-subprocess", question, "--evtfile", evt_file],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=clean_env,
    )
    active_proc["proc"] = proc
    return evt_file
