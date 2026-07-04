"""
测试脚本：同时开四个独立进程窗口发送 ask 请求，测试系统的并行能力
"""

import sys
import json
import httpx

def worker(worker_id: str):
    url = "http://localhost:8000/ask"
    # 让每个进程问稍微不一样的问题，涉及不同的工具调用，充分测试并发
    goals = {
        "1": "请帮我查一下北京的天气。",
        "2": "请搜索一下今天最新的科技新闻。",
        "3": "请帮我计算一下 12345 乘以 6789 再乘以珠海现在天气的温度数字，最后再除以3 等于多少？",
        "4": "请同时查一下上海的天气，并搜索一下上海有什么好玩的地方。"
    }
    
    payload = {"goal": goals.get(worker_id, f"你好，我是测试进程 {worker_id}")}
    
    print(f"================ 进程 {worker_id} 启动 ================")
    print(f"发送请求: {payload['goal']}\n")
    print("等待响应流...\n")
    
    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", url, json=payload) as response:
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str: 
                            continue
                        try:
                            event = json.loads(data_str)
                            evt_type = event.get("type")
                            
                            if evt_type == "content":
                                print(event["data"], end="", flush=True)
                            elif evt_type == "tool_call":
                                print(f"\n\n👉 [调用工具: {event['data']['name']}] ... ", end="", flush=True)
                            elif evt_type == "tool_result":
                                print("✅ [执行完毕]\n", end="", flush=True)
                            elif evt_type == "error":
                                print(f"\n\n❌ [错误]: {event['data']}")
                            elif evt_type == "conversation_id":
                                print(f"[分配对话ID: {event['data']}]\n")
                        except json.JSONDecodeError:
                            pass
                            
        print("\n\n================ 请求结束 ================")
    except Exception as e:
        print(f"\n\n❌ [请求异常] {e}")

if __name__ == '__main__':
    # 1. 子进程模式：执行具体的请求逻辑
    if len(sys.argv) == 3 and sys.argv[1] == "worker":
        worker(sys.argv[2])
        input("\n执行完毕，按回车键退出窗口...")
        
    # 2. 主进程模式：负责拉起 4 个新的 CMD 窗口
    else:
        import subprocess
        print("准备启动 4 个独立的 CMD 窗口进行并行测试...\n")
        
        for i in range(1, 5):
            print(f"正在拉起进程窗口 {i}...")
            # creationflags=subprocess.CREATE_NEW_CONSOLE (0x00000010) 在 Windows 下弹出新窗口
            subprocess.Popen(
                [sys.executable, __file__, "worker", str(i)],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
        print("\n拉起完毕！请查看系统弹出的 4 个黑框口，它们会同时向 Agent 发送流式请求。")