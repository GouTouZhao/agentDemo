import json
from internal.mysql import processor as db
from tools import logs
from tools.LLM import call_llm
from internal.prompt import MEMORY_LEVEL1_PROMPT, MEMORY_LEVEL2_PROMPT

def _format_messages_to_text(msgs: list[dict]) -> str:
    """将消息列表转为可读文本"""
    lines = []
    for m in msgs:
        msg_type = m.get("msg_type", "normal")
        if msg_type == "thinking":
            lines.append(f"助手(思考) [{m.get('seq_id', '')}]: {m.get('content', '')}")
        elif msg_type == "tool_call":
            try:
                tc = json.loads(m.get('content', '{}'))
                lines.append(f"助手(调用工具) [{m.get('seq_id', '')}]: {tc.get('function', {}).get('name')} 参数: {tc.get('function', {}).get('arguments')}")
            except:
                lines.append(f"助手(调用工具) [{m.get('seq_id', '')}]: {m.get('content', '')}")
        elif msg_type == "tool_result":
            try:
                tr = json.loads(m.get('content', '{}'))
                lines.append(f"系统(工具返回) [{m.get('seq_id', '')}]: {tr.get('result', m.get('content', ''))}")
            except:
                lines.append(f"系统(工具返回) [{m.get('seq_id', '')}]: {m.get('content', '')}")
        else:
            role = "用户" if m.get("role") == "user" else ("助手" if m.get("role") == "assistant" else "系统/工具")
            lines.append(f"{role} [{m.get('seq_id', '')}]: {m.get('content', '')}")
    return "\n".join(lines)

def check_and_generate_memory(conv_id: str):
    """
    检查对话轮数，符合条件则生成记忆
    - 每5轮生成一次 Level 1 局部总结
    - 每6轮生成一次 Level 2 全局更新
    """
    logs.info(f"后台触发记忆检查: conv={conv_id}")
    
    try:
        all_msgs = db.get_messages(conv_id, page=1, page_size=1000) # 取出所有消息，对于demo暂且够用
    except Exception as e:
        logs.error(f"提取消息失败: {e}")
        return

    # 按用户发问划分轮次（遇到一个 user 算一轮的开始）
    rounds = []
    current_round_msgs = []
    
    for msg in all_msgs:
        if msg["role"] == "user":
            if current_round_msgs:
                rounds.append(current_round_msgs)
            current_round_msgs = [msg]
        else:
            if current_round_msgs:
                current_round_msgs.append(msg)
    
    if current_round_msgs:
        rounds.append(current_round_msgs)

    total_rounds = len(rounds)
    logs.info(f"当前对话总轮数: {total_rounds}")

    # ===== 1. 第一层局部总结 (每 5 轮) =====
    if total_rounds > 0 and total_rounds % 5 == 0:
        logs.info(f"触发 Level 1 记忆生成 (第 {total_rounds} 轮)")
        # 取最近 5 轮
        recent_5_rounds = rounds[-5:]
        flat_msgs = [m for r in recent_5_rounds for m in r]
        if flat_msgs:
            start_seq = flat_msgs[0]["seq_id"]
            end_seq = flat_msgs[-1]["seq_id"]
            text_content = _format_messages_to_text(flat_msgs)
            
            prompt = MEMORY_LEVEL1_PROMPT.format(text_content=text_content)
            
            try:
                res = call_llm([{"role": "user", "content": prompt}])
                summary = res.get("content", "")
                if summary:
                    db.add_memory_level1(conv_id, start_seq, end_seq, summary)
                    logs.info(f"Level 1 记忆生成成功: seq {start_seq}-{end_seq}")
            except Exception as e:
                logs.error(f"Level 1 记忆生成失败: {e}")

    # ===== 2. 第二层全局更新 (每 6 轮) =====
    if total_rounds > 0 and total_rounds % 6 == 0:
        logs.info(f"触发 Level 2 记忆生成 (第 {total_rounds} 轮)")
        # 取最近 6 轮
        recent_6_rounds = rounds[-6:]
        flat_msgs = [m for r in recent_6_rounds for m in r]
        text_content = _format_messages_to_text(flat_msgs)
        
        old_level2 = db.get_memory_level2(conv_id)
        old_summary = old_level2["summary"] if old_level2 else "无"
        
        prompt = MEMORY_LEVEL2_PROMPT.format(old_summary=old_summary, text_content=text_content)
        
        try:
            res = call_llm([{"role": "user", "content": prompt}])
            new_summary = res.get("content", "")
            if new_summary:
                db.update_memory_level2(conv_id, new_summary)
                logs.info(f"Level 2 记忆更新成功")
        except Exception as e:
            logs.error(f"Level 2 记忆生成失败: {e}")
