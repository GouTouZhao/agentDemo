"""
MySQL 数据模型 — 仅维护对话，个人使用
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Conversation:
    """对话"""
    id: str                                          # UUID
    title: str                                       # 对话标题（首条消息摘要）
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Message:
    """对话中的单条消息"""
    id: int = 0                                      # 自增主键
    conversation_id: str = ""                        # 关联对话 ID
    seq_id: int = 0                                  # 对话内的序列号
    role: str = "user"                               # user / assistant / system / tool
    msg_type: str = "normal"                         # normal / thinking / tool_call / tool_result
    content: str = ""                                # 消息内容
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryLevel1:
    """第一层记忆：每5轮的局部总结"""
    id: int = 0
    conversation_id: str = ""
    start_seq: int = 0
    end_seq: int = 0
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryLevel2:
    """第二层记忆：每6轮的全局总结"""
    id: int = 0
    conversation_id: str = ""
    summary: str = ""
    updated_at: datetime = field(default_factory=datetime.now)