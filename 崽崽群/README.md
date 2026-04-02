# 崽崽群面板

多崽崽实时协作面板，支持自由聊天和结构化实验。

![截图](https://minimax-algeng-chat-tts.oss-cn-wulanchabu.aliyuncs.com/ccv2%2F2026-04-02%2FMiniMax-M2.7%2F2034973946167693603%2Fd5e2fd587dd34e8136d7bbafccc707f005ebbb7929eae2b1595c66a521c6ac08..png?Expires=1775211343&OSSAccessKeyId=LTAI5tGLnRTkBjLuYPjNcKQ8&Signature=wBtHIPycJmtrY%2BIMzWPLe%2Fc1oi4%3D)

## 功能特点

- **自由聊天**：选中多个崽崽，实时对话协作
- **结构化实验**：四轮渐进式讨论（开场 → 分析 → 讨论 → 总结）
- **@提及机制**：@指定崽崽定点提问
- **跨平台调度**：支持 VM SSH 和本机 Windows 双平台 agent
- **SSE 实时推送**：实验过程实时显示，不卡 UI

## 环境变量

```bash
# 必填：设置 HERD_VM_SSH 环境变量，格式：用户名@VM的SSH地址
export HERD_VM_SSH="your_user@your_vm_ip"
```

## 快速启动

```bash
cd 崽崽群
pip install fastapi uvicorn
python main.py
# 浏览器打开 http://localhost:8766
```

## Agent 接口

新增崽崽只需在 `崽崽群/config.py` 的 `HERD` 字典里加一项：

```python
"my_agent": {
    "name": "我的崽",
    "color": "#FF5722",
    "platform": "vm",         # "vm" = VM SSH / "win" = 本机 PowerShell
    "openclaw_agent": "xxx",  # openclaw agent 名称
    "think": "思考风格描述",
}
```

## 项目结构

```
崽崽群/
├── config.py       # 所有配置（HERD 定义 + 正则清理规则）
├── state.py        # 状态管理 + SSE 事件队列
├── agents.py       # agent 调度器
├── experiments.py  # 四轮实验逻辑
├── runners/
│   ├── vm.py       # VM SSH runner
│   └── win.py      # Windows PowerShell runner
├── routes/
│   ├── chat.py     # /chat
│   ├── exp.py      # /start
│   ├── events.py   # /events SSE
│   └── state.py    # /state
└── templates/
    └── index.html  # 前端面板
```
