from __future__ import annotations

"""
LLM 底层调用封装 — 基于 OpenAI 兼容接口调用阿里 Qwen
- call_llm:        同步调用，返回完整响应
- call_llm_stream: 流式调用，返回生成器
"""

from typing import Generator

from openai import OpenAI

from config.api_cfg import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from tools import logs
from tools.errs import msg_error

# 全局客户端实例
_client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)


def call_llm(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
) -> dict:
    """
    同步调用 LLM，返回完整的 choice 字典。

    Returns:
        {
            "role": "assistant",
            "content": "...",
            "tool_calls": [...]   # 可能为 None
        }
    """
    try:
        kwargs = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        logs.info(f"调用 LLM: model={LLM_MODEL}, messages_count={len(messages)}")
        response = _client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        result = {
            "role": "assistant",
            "content": choice.content or "",
        }
        if choice.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.tool_calls
            ]
        return result

    except Exception as e:
        raise msg_error(e, "LLM 调用失败")


def call_llm_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
) -> Generator[dict, None, None]:
    """
    流式调用 LLM，逐 chunk 返回。

    Yields:
        {"type": "content", "content": "..."}        — 文本片段
        {"type": "tool_calls", "tool_calls": [...]}   — 工具调用（流结束时聚合）
        {"type": "done"}                              — 流结束
    """
    try:
        kwargs = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        logs.info(f"流式调用 LLM: model={LLM_MODEL}, messages_count={len(messages)}")
        response = _client.chat.completions.create(**kwargs)

        # 聚合 tool_calls 片段
        tool_calls_buffer: dict[int, dict] = {}

        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # 文本内容
            if delta.content:
                yield {"type": "content", "content": delta.content}

            # 工具调用片段
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tc.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    buf = tool_calls_buffer[idx]
                    if tc.id:
                        buf["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            buf["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            buf["function"]["arguments"] += tc.function.arguments

        # 流结束，如有工具调用则返回
        if tool_calls_buffer:
            yield {
                "type": "tool_calls",
                "tool_calls": [tool_calls_buffer[i] for i in sorted(tool_calls_buffer.keys())],
            }

        yield {"type": "done"}

    except Exception as e:
        raise msg_error(e, "LLM 流式调用失败")
