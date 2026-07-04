"""
上下文聚合 — 从数据库加载对话历史，构建 LLM messages 列表
"""

from internal.context.context import build_context, append_context

__all__ = ["build_context", "append_context"]
