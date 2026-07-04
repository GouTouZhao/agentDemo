import json
from internal.mysql import processor as db
from internal.prompt import (
    SYSTEM_PROMPT,
    CONTEXT_LEVEL2_TEMPLATE,
    CONTEXT_LEVEL1_TEMPLATE,
    CONTEXT_QUOTE_OLD_TEMPLATE,
    CONTEXT_QUOTE_RECENT_TEMPLATE
)
from tools import logs

class ContextBuilder:
    @classmethod
    def build(cls, conv_id: str, quote_seq: int | None = None, include: list[str] = None) -> list[dict]:
        """
        按需加载和组装对话上下文。
        """
        if include is None:
            include = ["summary", "memory", "recent", "quote"]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 1. 顶层记忆 (summary)
        if "summary" in include:
            level2 = db.get_memory_level2(conv_id)
            if level2:
                messages.append({"role": "system", "content": CONTEXT_LEVEL2_TEMPLATE.format(summary=level2['summary'])})

        # 2. 底层记忆 (memory)
        if "memory" in include:
            level1_list = db.get_memory_level1(conv_id)
            if level1_list:
                l1_content = "\n".join([f"第 {m['start_seq']} 到 {m['end_seq']} 条对话总结: {m['summary']}" for m in level1_list])
                messages.append({"role": "system", "content": CONTEXT_LEVEL1_TEMPLATE.format(content=l1_content)})

        # 3. 获取近期消息
        recent_msgs = []
        recent_seqs = set()
        if "recent" in include or "quote" in include:
            all_msgs = db.get_all_messages(conv_id)
            recent_msgs = all_msgs[-10:] if len(all_msgs) > 10 else all_msgs
            recent_seqs = {m.get("seq_id") for m in recent_msgs if m.get("seq_id") is not None}

        # 4. 追问消息处理 (quote)
        if "quote" in include and quote_seq is not None:
            if quote_seq not in recent_seqs:
                quote_msg = db.get_message_by_seq(conv_id, quote_seq)
                if quote_msg:
                    messages.append({
                        "role": "system", 
                        "content": CONTEXT_QUOTE_OLD_TEMPLATE.format(
                            quote_seq=quote_seq, 
                            role=quote_msg['role'], 
                            content=quote_msg['content']
                        )
                    })
            else:
                messages.append({
                    "role": "system",
                    "content": CONTEXT_QUOTE_RECENT_TEMPLATE.format(quote_seq=quote_seq)
                })

        # 5. 最近消息 (recent)
        if "recent" in include:
            for msg in recent_msgs:
                msg_type = msg.get("msg_type", "normal")
                if msg_type == "tool_call":
                    try:
                        tc = json.loads(msg["content"])
                        if messages and messages[-1]["role"] == "assistant":
                            if "tool_calls" not in messages[-1]:
                                messages[-1]["tool_calls"] = []
                            messages[-1]["tool_calls"].append(tc)
                        else:
                            messages.append({"role": "assistant", "content": "", "tool_calls": [tc]})
                    except Exception as e:
                        logs.warning(f"解析 tool_call 失败: {e}")
                elif msg_type == "tool_result":
                    try:
                        res_data = json.loads(msg["content"])
                        messages.append({
                            "role": "tool",
                            "tool_call_id": res_data.get("tool_call_id", ""),
                            "content": res_data.get("result", "")
                        })
                    except Exception as e:
                        logs.warning(f"解析 tool_result 失败: {e}")
                else:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

        logs.info(f"ContextBuilder 组装完成: conv={conv_id}, 最终上下文长度={len(messages)}")
        return messages
