from __future__ import annotations

"""
MySQL 全局初始化 — 连接池 + 自动建库建表
"""

import pymysql
from dbutils.pooled_db import PooledDB

from config.mysql_cfg import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    MYSQL_CHARSET,
)
from tools import logs

# 全局连接池（延迟初始化）
_pool: PooledDB | None = None


# ================== 建库建表 SQL ==================
_CREATE_DB_SQL = f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` DEFAULT CHARSET {MYSQL_CHARSET}"

_CREATE_CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS `conversations` (
    `id`          VARCHAR(36)  PRIMARY KEY              COMMENT '对话ID (Snowflake)',
    `title`       VARCHAR(255) NOT NULL DEFAULT ''      COMMENT '对话标题',
    `created_at`  DATETIME     NOT NULL DEFAULT NOW()   COMMENT '创建时间',
    `updated_at`  DATETIME     NOT NULL DEFAULT NOW() ON UPDATE NOW() COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话表';
"""

_CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS `messages` (
    `id`              BIGINT       AUTO_INCREMENT PRIMARY KEY  COMMENT '消息ID',
    `conversation_id` VARCHAR(36)  NOT NULL             COMMENT '对话ID',
    `seq_id`          INT          NOT NULL             COMMENT '该对话中的序列号，从1开始',
    `role`            VARCHAR(20)  NOT NULL             COMMENT '角色 (user / assistant / system / tool)',
    `msg_type`        VARCHAR(20)  NOT NULL DEFAULT 'normal' COMMENT '类型 (normal/thinking/tool_call/tool_result)',
    `content`         TEXT         NOT NULL             COMMENT '消息内容',
    `created_at`      DATETIME     NOT NULL DEFAULT NOW() COMMENT '创建时间',
    INDEX `idx_conv_id` (`conversation_id`),
    INDEX `idx_conv_seq` (`conversation_id`, `seq_id`),
    FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息表';
"""

_CREATE_MEMORY_LEVEL1_TABLE = """
CREATE TABLE IF NOT EXISTS `memory_level1` (
    `id`              BIGINT       AUTO_INCREMENT PRIMARY KEY  COMMENT '主键ID',
    `conversation_id` VARCHAR(36)  NOT NULL                    COMMENT '关联对话ID',
    `start_seq`       INT          NOT NULL                    COMMENT '起始消息序号',
    `end_seq`         INT          NOT NULL                    COMMENT '结束消息序号',
    `summary`         TEXT         NOT NULL                    COMMENT '总结内容',
    `created_at`      DATETIME     NOT NULL DEFAULT NOW()      COMMENT '创建时间',
    INDEX `idx_conv_id` (`conversation_id`),
    FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='底层记忆表';
"""

_CREATE_MEMORY_LEVEL2_TABLE = """
CREATE TABLE IF NOT EXISTS `memory_level2` (
    `id`              BIGINT       AUTO_INCREMENT PRIMARY KEY  COMMENT '主键ID',
    `conversation_id` VARCHAR(36)  NOT NULL UNIQUE             COMMENT '关联对话ID(一对一)',
    `summary`         TEXT         NOT NULL                    COMMENT '全局总结内容',
    `updated_at`      DATETIME     NOT NULL DEFAULT NOW() ON UPDATE NOW() COMMENT '更新时间',
    FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='顶层记忆表';
"""


def _ensure_database() -> None:
    """确保数据库存在（不选定 database 连接后执行 CREATE DATABASE）"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset=MYSQL_CHARSET,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(_CREATE_DB_SQL)
        conn.commit()
        logs.info(f"数据库 `{MYSQL_DATABASE}` 已就绪")
    finally:
        conn.close()


def _ensure_tables(conn) -> None:
    """确保表存在"""
    with conn.cursor() as cur:
        cur.execute(_CREATE_CONVERSATIONS_TABLE)
        cur.execute(_CREATE_MESSAGES_TABLE)
        cur.execute(_CREATE_MEMORY_LEVEL1_TABLE)
        cur.execute(_CREATE_MEMORY_LEVEL2_TABLE)
    conn.commit()
    logs.info("数据表 conversations / messages / memory 已就绪")


def init_db() -> None:
    """
    初始化数据库：
    1. 创建 database（如不存在）
    2. 创建连接池
    3. 创建表（如不存在）
    """
    global _pool

    # 1. 建库
    _ensure_database()

    # 2. 连接池
    _pool = PooledDB(
        creator=pymysql,
        maxconnections=10,
        mincached=2,
        maxcached=5,
        blocking=True,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset=MYSQL_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
    )
    logs.info("MySQL 连接池已初始化")

    # 3. 建表
    conn = _pool.connection()
    try:
        _ensure_tables(conn)
    finally:
        conn.close()


def get_connection():
    """从连接池获取连接"""
    if _pool is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _pool.connection()
