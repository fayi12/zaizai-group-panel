# -*- coding: utf-8 -*-
"""
崽崽群 启动脚本
用法: python run.py
"""
import sys
from pathlib import Path

# 确保崽崽群包在 sys.path
_ROOT = Path(__file__).resolve().parent / "崽崽群"
if str(_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(_ROOT.parent))

if __name__ == "__main__":
    from崽崽群.main import app
    import uvicorn

    print(f"\n  崽崽群实时面板 v2.0\n  浏览器打开: http://localhost:8766\n")
    uvicorn.run(app, host="0.0.0.0", port=8766, log_level="warning")
