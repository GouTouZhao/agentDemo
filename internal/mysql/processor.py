from __future__ import annotations

"""
MySQL CRUD 封装 — 对话与消息的增删改查
"""

from datetime import datetime
from typing import Optional

from internal.mysql.init import get_connection
from internal.mysql.model import Conversation, Message
from tools import logs
from tools.errs import msg_error


# ==================== 对话 ====================

def create_conversation(conv_id: str, title: str) -> Conversation:
    """新建对话"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (id, title) VALUES (%s, %s)",
                (conv_id, title),
            )
        conn.commit()
        logs.info(f"新建对话: {conv_id} — {title}")
        return Conversation(id=conv_id, title=title)
    except Exception as e:
        conn.rollback()
        raise msg_error(e, "新建对话失败")
    finally:
        conn.close()


def list_conversations() -> list[dict]:
    """列出所有对话（按更新时间倒序）"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
            )
            return cur.fetchall()
    except Exception as e:
        raise msg_error(e, "查询对话列表失败")
    finally:
        conn.close()


def get_conversation(conv_id: str) -> Optional[dict]:
    """获取单个对话信息"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s",
                (conv_id,),
            )
            return cur.fetchone()
    except Exception as e:
        raise msg_error(e, "查询对话失败")
    finally:
        conn.close()


def update_conversation_title(conv_id: str, title: str) -> None:
    """更新对话标题"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE conversations SET title = %s WHERE id = %s",
                (title, conv_id),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise msg_error(e, "更新对话标题失败")
    finally:
        conn.close()


def delete_conversation(conv_id: str) -> None:
    """删除对话及其所有消息"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE id = %s", (conv_id,))
        conn.commit()
        logs.info(f"已删除对话: {conv_id}")
    except Exception as e:
        conn.rollback()
        raise msg_error(e, "删除对话失败")
    finally:
        conn.close()


# ==================== 消息 ====================

def add_message(conv_id: str, role: str, content: str, msg_type: str = "normal") -> int:
    """添加一条消息，自动计算 seq_id，返回消息 ID"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 获取当前最大 seq_id
            cur.execute("SELECT MAX(seq_id) as max_seq FROM messages WHERE conversation_id = %s", (conv_id,))
            row = cur.fetchone()
            seq_id = (row["max_seq"] + 1) if row and row["max_seq"] is not None else 0

            cur.execute(
                "INSERT INTO messages (conversation_id, seq_id, role, content, msg_type) VALUES (%s, %s, %s, %s, %s)",
                (conv_id, seq_id, role, content, msg_type),
            )
            msg_id = cur.lastrowid
        conn.commit()
        logs.info(f"添加消息: conv={conv_id}, role={role}, id={msg_id}")
        return msg_id
    except Exception as e:
        conn.rollback()
        raise msg_error(e, "添加消息失败")
    finally:
        conn.close()


def get_messages(conv_id: str, page: int = 1, page_size: int = 20) -> list[dict]:
    """分页获取对话消息（按时间正序）"""
    offset = (page - 1) * page_size
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, conversation_id, seq_id, role, content, msg_type, created_at "
                "FROM messages WHERE conversation_id = %s "
                "ORDER BY seq_id ASC LIMIT %s OFFSET %s",
                (conv_id, page_size, offset),
            )
            return cur.fetchall()
    except Exception as e:
        raise msg_error(e, "查询消息失败")
    finally:
        conn.close()


def get_all_messages(conv_id: str) -> list[dict]:
    """获取对话的全部消息（用于构建上下文）"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content, seq_id, msg_type FROM messages "
                "WHERE conversation_id = %s ORDER BY seq_id ASC",
                (conv_id,),
            )
            return cur.fetchall()
    except Exception as e:
        raise msg_error(e, "查询全部消息失败")
    finally:
        conn.close()


def get_message_count(conv_id: str) -> int:
    """获取对话消息总数"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM messages WHERE conversation_id = %s",
                (conv_id,),
            )
            row = cur.fetchone()
            return row["cnt"] if row else 0
    except Exception as e:
        raise msg_error(e, "查询消息数量失败")
    finally:
        conn.close()


def get_message_by_seq(conv_id: str, seq_id: int) -> Optional[dict]:
    """根据 seq_id 获取单条消息"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content, seq_id, msg_type, created_at FROM messages "
                "WHERE conversation_id = %s AND seq_id = %s",
                (conv_id, seq_id),
            )
            return cur.fetchone()
    except Exception as e:
        raise msg_error(e, "查询单条消息失败")
    finally:
        conn.close()


# ==================== 记忆 ====================

def add_memory_level1(conv_id: str, start_seq: int, end_seq: int, summary: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_level1 (conversation_id, start_seq, end_seq, summary) VALUES (%s, %s, %s, %s)",
                (conv_id, start_seq, end_seq, summary),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise msg_error(e, "添加底层记忆失败")
    finally:
        conn.close()


def get_memory_level1(conv_id: str) -> list[dict]:
    """获取所有底层记忆"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT start_seq, end_seq, summary FROM memory_level1 "
                "WHERE conversation_id = %s ORDER BY start_seq ASC",
                (conv_id,),
            )
            return cur.fetchall()
    except Exception as e:
        raise msg_error(e, "查询底层记忆失败")
    finally:
        conn.close()


def update_memory_level2(conv_id: str, summary: str) -> None:
    """更新顶层记忆，存在则更新，不存在则插入"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_level2 (conversation_id, summary) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE summary = VALUES(summary)",
                (conv_id, summary),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise msg_error(e, "更新顶层记忆失败")
    finally:
        conn.close()


def get_memory_level2(conv_id: str) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT summary FROM memory_level2 WHERE conversation_id = %s",
                (conv_id,),
            )
            return cur.fetchone()
    except Exception as e:
        raise msg_error(e, "查询顶层记忆失败")
    finally:
        conn.close()

