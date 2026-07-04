"""
Agent Runtime — 核心运行时 (状态机版本)

实现 Agent 主循环：
  接收 goal → 构建上下文 → [THINK] → [ACT] → [OBSERVE] → 流式输出
"""

from internal.runtime.runtime import AgentRuntime, agent_runtime, MAX_TOOL_ROUNDS

__all__ = ["AgentRuntime", "agent_runtime", "MAX_TOOL_ROUNDS"]
