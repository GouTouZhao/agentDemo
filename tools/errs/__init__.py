from __future__ import annotations

"""
统一错误处理模块
- MsgError:  带提示信息和状态码的错误
- new_error: 新建错误
- msg_error: 给已有错误打上提示和状态码
"""

import traceback
from tools import logs


class MsgError(Exception):
    """带有用户友好提示和 HTTP 状态码的错误"""

    def __init__(self, message: str, code: int = 500, original: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.original = original

    def __str__(self) -> str:
        base = f"[{self.code}] {self.message}"
        if self.original:
            base += f" | 原始错误: {self.original}"
        return base


def new_error(msg: str, code: int = 500) -> MsgError:
    """
    新建一个 MsgError，同时：
    - 追踪调用栈，获取出错位置
    - 在控制台输出红色错误日志
    """
    # 获取调用方的栈帧信息
    stack = traceback.extract_stack(limit=3)
    caller = stack[-2] if len(stack) >= 2 else None

    detail = msg
    if caller:
        detail = f"{msg}  ← {caller.filename}:{caller.lineno} in {caller.name}"

    logs.error(detail)
    return MsgError(message=msg, code=code)


def msg_error(err: Exception, msg: str, code: int = 500) -> MsgError:
    """
    给已有的 Exception 打上用户提示和状态码，同时：
    - 追踪原始错误的完整调用栈
    - 在控制台输出红色错误日志
    """
    # 获取原始异常的 traceback 信息
    tb_str = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    detail = f"{msg}\n--- 原始异常 ---\n{tb_str}"

    logs.error(detail)
    return MsgError(message=msg, code=code, original=err)
