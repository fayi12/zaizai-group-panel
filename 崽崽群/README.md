# 崽崽群面板

多崽崽实时协作面板，支持自由聊天和结构化实验。

## 环境变量

```bash
# 必填：VM SSH 连接地址（ip 地址和用户名）
export HERD_VM_SSH="fayi@172.17.26.221"
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
├── experiments.py   # 四轮实验逻辑
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
