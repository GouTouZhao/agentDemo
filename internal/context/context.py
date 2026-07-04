from internal.context.builder import ContextBuilder

def build_context(conv_id: str, quote_seq: int | None = None) -> list[dict]:
    """
    为了兼容老代码，保留此函数，底层调用 ContextBuilder。
    """
    return ContextBuilder.build(conv_id, quote_seq=quote_seq)

def append_context(messages: list[dict], role: str, content: str) -> list[dict]:
    """
    向上下文追加一条消息（不写入数据库，仅内存操作）。
    """
    messages.append({"role": role, "content": content})
    return messages
