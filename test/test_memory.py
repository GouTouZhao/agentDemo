import urllib.request
import json
import time

URL = "http://127.0.0.1:8000/ask"

def ask_agent(goal, conv_id=None):
    payload = {"goal": goal}
    if conv_id:
        payload["conv_id"] = conv_id
    
    req = urllib.request.Request(
        URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}, 
        method='POST'
    )
    
    current_conv_id = conv_id
    full_answer = ""
    
    try:
        with urllib.request.urlopen(req) as response:
            for line in response:
                decoded_line = line.decode('utf-8').strip()
                if decoded_line.startswith("data: "):
                    try:
                        data = json.loads(decoded_line[6:])
                        if data["type"] == "conversation_id":
                            current_conv_id = data["data"]
                        elif data["type"] == "content":
                            full_answer += data["data"]
                        elif data["type"] == "error":
                            full_answer += f"\n[Error] {data['data']}"
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        full_answer += f"\n[HTTP Request Failed] {e}"
        
    return current_conv_id, full_answer

def run_test():
    # 构造32条信息，首条注入上下文，后续拉长对话轮次，最后几条测试记忆提取
    messages = [
        "你好，我叫李华，今年25岁，住在北京，喜欢打篮球，有一只宠物狗叫'大黄'。",
        "1+1等于几？",
        "背诵李白的《静夜思》",
        "中国的首都在哪里？",
        "世界上最高的山峰叫什么？",
        "现在北京的气温怎么样",
        "苹果的英文是什么？",
        "你知道相对论是谁提出的吗？",
        "水是由什么元素组成的？",
        "地球自转一圈需要多久？",
        
        "推荐一部科幻电影。",
        "用一段话描述一下春天。",
        "太阳系最大的行星是哪个？",
        "《三国演义》的作者是谁？",
        "什么是人工智能？",
        "请翻译：How are you?",
        "今天星期几？(你可以随便猜)",
        "你能讲个笑话吗？",
        "简述一下牛顿第一定律。",
        "人体最大的器官是什么？",
        
        "猫一般能活多少年？",
        "世界上最长的河是哪条？",
        "请写出一个Python的print语句。",
        "蒙娜丽莎是谁画的？",
        "圆周率的前五位是多少？",
        "一千克等于多少克？",
        "空气中含量最多的气体是什么？",
        "音乐有哪七个基本音符？",
        "彩虹有哪些颜色？",
        
        "测试一下你的记忆力，请问我叫什么名字？",
        "我现在几岁了？我住在哪个城市？",
        "我的宠物狗叫什么名字？我平时喜欢做什么运动？"
    ]
    
    print(f"开始执行 32 轮记忆测试...\n总计信息数: {len(messages)}")
    
    conv_id = None
    for i, msg in enumerate(messages):
        print(f"\n--- 第 {i+1} 轮 ---")
        print(f"用户: {msg}")
        
        start_time = time.time()
        conv_id, answer = ask_agent(msg, conv_id)
        elapsed = time.time() - start_time
        
        print(f"Agent ({elapsed:.1f}s): {answer}")
        
        # 停顿2秒，一是模拟真实用户打字间隔，二是避免瞬时高频请求触发大模型API的限流
        time.sleep(2)

if __name__ == "__main__":
    run_test()
