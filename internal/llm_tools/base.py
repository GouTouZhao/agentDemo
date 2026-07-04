import json
import concurrent.futures
from typing import Callable, Optional, Generator, Any
from tools import logs
from internal.mysql import processor as db

def execute_tools_parallel(
    tool_calls: list,
    executor: Any,
    conv_id: str,
    current_results: list
) -> Generator[dict, None, None]:
    """
    统一封装的工具调用函数，支持并行调用多个工具，解耦 runtime。
    """
    # 先按顺序 yield 工具调用事件，并记录数据库
    for tc in tool_calls:
        func_name = tc["function"]["name"]
        func_args = tc["function"]["arguments"]
        yield {
            "type": "tool_call",
            "data": {"name": func_name, "arguments": func_args}
        }
        db.add_message(conv_id, "assistant", json.dumps(tc, ensure_ascii=False), "tool_call")

    def _exec_single(tc):
        func_name = tc["function"]["name"]
        func_args = tc["function"]["arguments"]
        tool_call_id = tc["id"]
        result = executor.execute(func_name, func_args)
        return func_name, tool_call_id, result

    results_map = {}
    # 使用线程池并行执行工具
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(tool_calls))) as thread_executor:
        futures = [thread_executor.submit(_exec_single, tc) for tc in tool_calls]
        for future in concurrent.futures.as_completed(futures):
            func_name, tool_call_id, result = future.result()
            
            yield {
                "type": "tool_result",
                "data": {"name": func_name, "result": result}
            }
            
            result_data = json.dumps({"tool_call_id": tool_call_id, "result": result}, ensure_ascii=False)
            db.add_message(conv_id, "tool", result_data, "tool_result")
            
            results_map[tool_call_id] = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result,
            }
            
    # 按原始 tool_calls 的顺序整理 current_results
    for tc in tool_calls:
        current_results.append(results_map[tc["id"]])

class BaseTool:
    """
    Agent 工具抽象基类
    """
    name: str = ""
    schema: dict = {}
    timeout: int = 10
    retry: int = 0
    fallback: Optional[Callable] = None

    def execute(self, **kwargs) -> str:
        """
        执行工具的抽象方法。由子类实现具体逻辑。
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def run_with_retry(self, **kwargs) -> str:
        """
        带重试和异常处理的执行包装器。
        """
        attempts = 0
        max_attempts = self.retry + 1
        last_exception = None

        while attempts < max_attempts:
            try:
                logs.info(f"执行工具: {self.name}, 参数: {kwargs} (第 {attempts + 1}/{max_attempts} 次)")
                return self.execute(**kwargs)
            except Exception as e:
                attempts += 1
                last_exception = e
                logs.warning(f"工具 {self.name} 执行失败 ({attempts}/{max_attempts}): {e}")

        if self.fallback:
            logs.info(f"触发工具 {self.name} 的 fallback 逻辑")
            return self.fallback(**kwargs, exception=last_exception)
        
        return f"工具执行失败 (已重试 {self.retry} 次): {last_exception}"
