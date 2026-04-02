# -*- coding: utf-8 -*-
"""
崽崽群 启动脚本
用法: python run.py
"""
import sys
from pathlib import Path

# 确保崽崽群包在 sys.path
pkg = "崽崽群"
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

if __name__ == "__main__":
    # 用 __import__ 避免中文包名编码问题
    mod = __import__(f"{pkg}.main", fromlist=["app"])
    import uvicorn

    print(f"\n  崽崽群实时面板 v2.0\n  浏览器打开: http://localhost:8766\n")
    uvicorn.run(mod.app, host="0.0.0.0", port=8766, log_level="warning")
