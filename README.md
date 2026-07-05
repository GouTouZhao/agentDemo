#  Minimal Agent Runtime

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

## 工具能力
- **大模型使用** ——阿里 QWEN-max

- 🧮 **计算器** — 安全的数学表达式计算（支持 +、-、*、/、**、sqrt、sin、cos 等）
- 🔍 **网络搜索** — 阿里搜索 API
- 🌤 **天气查询** — 和风天气实时数据


## 系统架构与设计说明

### 1. 运行方式 (Execution Mode)
Agent 运行时采用 **流式状态机** 设计。核心组件包括 Planner（大模型调度）、ToolRouter（工具路由）和 Executor（工具执行）。
- **运行主循环**：采用 `THINK -> ACT -> OBSERVE -> THINK` 的状态机循环，单次请求最大循环限制为 10 轮，防止死循环。
- **流式输出 (SSE)**：从系统接收到请求开始，通过 Python Generator 实时 `yield` 当前的中间状态（如对话 ID、思考过程、工具调用信息、工具执行结果、文本片段等）。通过 FastAPI 的 `StreamingResponse` 透传给前端，实现极低延迟的交互体验。
- **并发与错误处理**：通过 `execute_tools_parallel` 机制，系统能够并发执行 Planner 下发的多个独立工具调用任务，提升处理效率，同时捕获单工具错误而不阻塞主流程。

### 2. 系统设计 (System Design)
系统整体为**分层解耦架构**，确保了高度的可扩展性和可维护性：
- **API 层 (`cmd/`)**：负责 HTTP 服务，提供对话流式拉取、历史记录查询等能力。
- **运行层 (`internal/runtime`)**：Agent 的核心大脑。管理大模型调用和工具集路由。
- **上下文管理 (`internal/context`)**：负责按需提取历史记忆，动态构建 Prompt 注入给 LLM。
- **持久化层 (`internal/mysql`)**：提供对话、消息及分层记忆的 MySQL 落盘 CRUD 封装。
- **工具层 (`internal/llm_tools`)**：业务动作的封装（如数学计算器、网络搜索、天气查询），支持独立注册与热插拔。

### 3. Memory 机制 (记忆召回与放置)
系统采用了双层记忆聚合与动态窗口结合的机制，来应对长上下文遗忘灾难。

**生成时机 (Generation Timing):**
- **底层记忆 (Level 1)**：局部总结。以用户发问（一轮交互）为粒度，每满 **5 轮** 交互，系统会自动在后台触发，抽取这 5 轮的对话内容交由 LLM 生成分段摘要，存入底层记忆表。
- **顶层记忆 (Level 2)**：全局总结。每满 **6 轮** 交互，系统将已有的 Level 2 摘要和最近 6 轮对话拼接，让 LLM 进行一次全局知识的合并更新（Update），存入顶层记忆表。

**召回时机与放置方式 (Recall & Placement):**
当用户发起新提问（或 `ContextBuilder` 构建上下文）时，会按以下顺序放置到发给 LLM 的 `messages` (Prompt Context) 数组中：
1. **系统预设 (System)**：在最开头放置最顶级的 `SYSTEM_PROMPT`（Agent 人设与核心规则）。
2. **顶层记忆 (Level 2 Summary)**：如果存在，以 `system` 角色紧随其后放置全局摘要，让模型最先了解历史核心事实。
3. **底层记忆 (Level 1 Memory)**：如果存在，以 `system` 角色放置，按时间线列出各分段的历史记录摘要，提供重要细节补充。
4. **追问信息 (Quote)**：如果用户对历史特定消息发起引用（`quote_seq`），会将引用的那条具体消息原文组装成 System Prompt 进行重点提示。
5. **短期记忆 (Recent Messages)**：最后，系统会召回并追加对话中最近 10 条真实消息流（包括工具调用、执行结果、思考过程），确保短期上下文的丝滑衔接和准确应答。
