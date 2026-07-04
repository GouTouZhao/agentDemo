from __future__ import annotations

"""
Agent 系统 HTTP API 入口

接口：
  POST /ask            — 流式提问（SSE）
  GET  /tasks          — 列出所有对话
  GET  /tasks/{conv_id} — 对话详情（分页）
"""

import json
import sys
import os

# 将项目根目录加入 sys.path（确保模块可被正确导入）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from internal.mysql.init import init_db
from internal.mysql import processor as db
from internal.runtime import agent_runtime
from tools import logs
from tools.errs import MsgError
import threading

# ==================== FastAPI 应用 ====================
app = FastAPI(
    title="Minimal Agent Runtime",
    description="最小可用 Agent 系统 API",
    version="0.1.0",
)

# CORS 配置（允许前端跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 全局任务列表 ====================
# 键: 对话 ID, 值: 任务状态信息
active_tasks: dict[str, dict] = {}

conversation_locks: dict[str, threading.Lock] = {}
global_dict_lock = threading.Lock()

def get_conv_lock(conv_id: str) -> threading.Lock:
    with global_dict_lock:
        if conv_id not in conversation_locks:
            conversation_locks[conv_id] = threading.Lock()
        return conversation_locks[conv_id]


# ==================== 启动事件 ====================
@app.on_event("startup")
def startup():
    """应用启动时初始化数据库"""
    logs.info("========== Agent 系统启动 ==========")
    init_db()
    logs.info("========== 初始化完成 ==========")


# ==================== 请求模型 ====================
class AskRequest(BaseModel):
    goal: str
    conv_id: str | None = None  # 可选：继续已有对话
    quote_seq: int | None = None # 可选：追问引用的历史消息序列号


# ==================== 接口 ====================

@app.post("/ask")
async def ask_question(req: AskRequest):
    """
    提问接口 — HTTP Streaming (SSE) 流式返回

    请求体: {"goal": "你的问题", "conv_id": "可选对话ID"}
    响应: text/event-stream，每行为 JSON:
        {"type": "conversation_id", "data": "..."}
        {"type": "content", "data": "..."}
        {"type": "tool_call", "data": {...}}
        {"type": "tool_result", "data": {...}}
        {"type": "done", "data": ""}
    """
    logs.info(f"收到提问: goal={req.goal[:100]}, conv_id={req.conv_id}")

    def event_generator():
        # 如果是已有对话，获取对应的锁；如果是新对话，则使用一个不阻塞的假锁
        import contextlib
        lock_ctx = get_conv_lock(req.conv_id) if req.conv_id else contextlib.nullcontext()
        
        with lock_ctx:
            conv_id_used = req.conv_id
            try:
                for event in agent_runtime.run(goal=req.goal, conv_id=req.conv_id, quote_seq=req.quote_seq):
                    # 记录活跃任务
                    if event["type"] == "conversation_id":
                        conv_id_used = event["data"]
                        active_tasks[conv_id_used] = {"status": "running", "goal": req.goal}

                    # SSE 格式：data: {json}\n\n
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    # 结束时更新任务状态
                    if event["type"] in ("done", "error"):
                        if conv_id_used and conv_id_used in active_tasks:
                            active_tasks[conv_id_used]["status"] = "completed"

            except MsgError as e:
                yield f"data: {json.dumps({'type': 'error', 'data': e.message}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logs.error(f"流式输出异常: {e}")
                yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"
            
            # 对话结束（或报错）后，后台触发记忆生成
            if conv_id_used:
                # 动态导入避免循环依赖
                from internal.context.memory import check_and_generate_memory
                threading.Thread(target=check_and_generate_memory, args=(conv_id_used,)).start()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/tasks")
async def list_tasks():
    """
    列出所有对话

    返回: {"code": 0, "data": [...]}
    """
    try:
        conversations = db.list_conversations()
        # 序列化 datetime
        for conv in conversations:
            for key in ("created_at", "updated_at"):
                if conv.get(key):
                    conv[key] = conv[key].isoformat()

        return {
            "code": 0,
            "data": conversations,
            "active_tasks": {k: v for k, v in active_tasks.items()},
        }
    except MsgError as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{conv_id}")
async def task_detail(
    conv_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(1, ge=1, le=100, description="每页消息数（默认1条，逐条加载）"),
):
    """
    对话详情 — 分页获取消息

    - 打开对话时请求第一页（第一条消息）
    - 每次请求加载一条消息 (page_size=1)

    返回: {"code": 0, "data": {"conversation": {...}, "messages": [...], "total": N, "page": P}}
    """
    try:
        # 获取对话信息
        conversation = db.get_conversation(conv_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"对话不存在: {conv_id}")

        # 序列化 datetime
        for key in ("created_at", "updated_at"):
            if conversation.get(key):
                conversation[key] = conversation[key].isoformat()

        # 获取消息（分页）
        messages = db.get_messages(conv_id, page=page, page_size=page_size)
        for msg in messages:
            if msg.get("created_at"):
                msg["created_at"] = msg["created_at"].isoformat()

        total = db.get_message_count(conv_id)

        return {
            "code": 0,
            "data": {
                "conversation": conversation,
                "messages": messages,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }
    except HTTPException:
        raise
    except MsgError as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cmd.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
