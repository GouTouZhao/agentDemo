from __future__ import annotations

import json
from typing import Generator

from internal.context import build_context, append_context
from internal.runtime.core import Planner, ToolRouter, Executor
from internal.llm_tools.base import execute_tools_parallel
from internal.mysql import processor as db
from tools import logs
from tools.snowflake import gen_id

# 最大工具调用轮数（防止无限循环）
MAX_TOOL_ROUNDS = 10

class AgentRuntime:
    """分层解耦的 Agent 运行时"""
    
    def __init__(self):
        self.router = ToolRouter()
        self.executor = Executor(self.router)
        self.planner = Planner(self.router)

    def run(self, goal: str, conv_id: str | None = None, quote_seq: int | None = None) -> Generator[dict, None, None]:
        """
        Agent 主入口 — 流式生成器。

        Args:
            goal: 用户的问题 / 目标
            conv_id: 对话 ID（为 None 则新建对话）

        Yields:
            {"type": "conversation_id", "data": "..."}     — 对话 ID
            {"type": "content", "data": "..."}             — 文本片段
            {"type": "tool_call", "data": {...}}            — 工具调用信息
            {"type": "tool_result", "data": {...}}          — 工具执行结果
            {"type": "done", "data": ""}                   — 结束标记
            {"type": "error", "data": "..."}               — 错误信息
        """
        try:
            # ===== 1. 创建或复用对话 =====
            is_new = conv_id is None
            if is_new:
                conv_id = gen_id()
                title = goal[:50].replace("\n", " ").strip() or "新对话"
                db.create_conversation(conv_id, title)
                logs.info(f"新建对话: {conv_id}")

            yield {"type": "conversation_id", "data": conv_id}

            # ===== 2. 存储用户消息 =====
            db.add_message(conv_id, "user", goal)

            # ===== 3. 构建上下文 =====
            # 已封装长context压缩
            messages = build_context(conv_id, quote_seq)

            # ===== 4. 状态机循环 =====
            state = "THINK"
            rounds = 0
            
            current_tool_calls = []
            current_thinking = ""
            current_results = []

            while rounds < MAX_TOOL_ROUNDS:
                if state == "THINK":
                    logs.info(f"[THINK] 状态机循环 第 {rounds + 1} 轮")
                    
                    response = self.planner.decide(messages)
                    tool_calls = response.get("tool_calls")
                    
                    if not tool_calls:
                        # 无工具调用，走流式输出
                        full_content = ""
                        for chunk in self.planner.stream_answer(messages):
                            if chunk["type"] == "content":
                                full_content += chunk["content"]
                                yield {"type": "content", "data": chunk["content"]}
                            elif chunk["type"] == "tool_calls":
                                tool_calls = chunk["tool_calls"]
                                break
                            elif chunk["type"] == "done":
                                break
                                
                        if not tool_calls:
                            # 真正结束
                            if full_content:
                                db.add_message(conv_id, "assistant", full_content)
                            yield {"type": "done", "data": ""}
                            return
                            
                    # 转入 ACT
                    current_tool_calls = tool_calls
                    current_thinking = response.get("content", "")
                    state = "ACT"

                elif state == "ACT":
                    logs.info(f"[ACT] 准备执行 {len(current_tool_calls)} 个工具")
                    
                    if current_thinking:
                        yield {"type": "thinking", "data": current_thinking}
                        db.add_message(conv_id, "assistant", current_thinking, "thinking")
                        
                    assistant_msg = {"role": "assistant", "content": current_thinking}
                    if current_tool_calls:
                        assistant_msg["tool_calls"] = current_tool_calls
                    messages.append(assistant_msg)
                    
                    current_results = []
                    
                    yield from execute_tools_parallel(current_tool_calls, self.executor, conv_id, current_results)
                        
                    state = "OBSERVE"

                elif state == "OBSERVE":
                    logs.info(f"[OBSERVE] 注入结果并回到 THINK")
                    messages.extend(current_results)
                    rounds += 1
                    state = "THINK"

            # 达到最大轮数
            logs.warning(f"Agent 循环达到最大轮数 {MAX_TOOL_ROUNDS}")
            yield {"type": "content", "data": "已达到最大轮数限制,发送continue继续作答"}
            yield {"type": "done", "data": ""}

        except Exception as e:
            logs.error(f"Agent 运行异常: {e}")
            yield {"type": "error", "data": str(e)}

# 全局单例
agent_runtime = AgentRuntime()
