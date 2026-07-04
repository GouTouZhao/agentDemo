"""
日志模块 — 控制台彩色输出
- error:   红色
- warning: 黄色
- info:    无颜色
"""

import sys
from datetime import datetime

from colorama import Fore, Style, init as colorama_init

# 初始化 colorama（Windows 兼容）
colorama_init(autoreset=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def info(msg: str) -> None:
    """普通日志 — 无颜色"""
    print(f"[{_timestamp()}] [INFO]  {msg}")


def warning(msg: str) -> None:
    """警告日志 — 黄色"""
    print(f"{Fore.YELLOW}[{_timestamp()}] [WARN]  {msg}{Style.RESET_ALL}")


def error(msg: str) -> None:
    """错误日志 — 红色，输出到 stderr"""
    print(
        f"{Fore.RED}[{_timestamp()}] [ERROR] {msg}{Style.RESET_ALL}",
        file=sys.stderr,
    )
