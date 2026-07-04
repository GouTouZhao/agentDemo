# 🤖 Minimal Agent Runtime

从零构建的最小可用 Agent 系统，支持流式对话、工具调用（计算器/搜索/天气）、MySQL 对话持久化。

## 项目结构

```
cmd/            → HTTP API 入口（FastAPI）
config/         → 配置管理（API密钥 / 数据库配置）
internal/       → 核心逻辑
  ├── runtime/  → Agent 运行时（主循环）
  ├── mysql/    → 数据库层（模型/初始化/CRUD）
  ├── llm_tools/→ 工具层（计算器/搜索/天气）
  ├── context/  → 上下文聚合
  └── prompt/   → 提示词管理
tools/          → 基础工具
  ├── logs/     → 日志（彩色输出）
  ├── errs/     → 错误处理
  └── LLM/      → LLM 调用封装
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

- `config/api_cfg.py` — API 密钥（已配置）
- `config/mysql_cfg.py` — MySQL 连接参数（默认 root/422624）

### 3. 启动

```bash
# 从项目根目录启动
python -m cmd.main
```

服务启动后自动创建数据库和表，访问 `http://localhost:8000`

### 4. API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ask` | 流式提问（SSE），请求体: `{"goal": "你的问题"}` |
| GET  | `/tasks` | 列出所有对话 |
| GET  | `/tasks/{conv_id}?page=1&page_size=1` | 对话详情（分页） |

### 5. 测试

```bash
# 流式提问
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"goal": "你好，请介绍一下你自己"}' \
  --no-buffer

# 列出对话
curl http://localhost:8000/tasks

# 对话详情
curl http://localhost:8000/tasks/<conv_id>?page=1&page_size=10
```

## 工具能力

- 🧮 **计算器** — 安全的数学表达式计算（支持 +、-、*、/、**、sqrt、sin、cos 等）
- 🔍 **网络搜索** — 百度千帆搜索 API
- 🌤 **天气查询** — 和风天气实时数据

## 技术栈

- **Python 3.11+**
- **FastAPI** — 异步 Web 框架
- **Qwen Max** — 阿里通义千问大模型（OpenAI 兼容接口）
- **MySQL** — 对话持久化
- **SSE** — 流式响应

