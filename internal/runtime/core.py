import json
from typing import Generator

from internal.llm_tools import AVAILABLE_TOOLS
from tools.LLM import call_llm, call_llm_stream
from tools import logs

class ToolRouter:
    """
    工具路由，管理所有可用工具的注册和分发
    """
    def __init__(self):
        self.tools = {t.name: t() for t in AVAILABLE_TOOLS}
        
    def get_schema_list(self) -> list[dict]:
        return [t.schema for t in self.tools.values()]
        
    def get_tool(self, name: str):
        return self.tools.get(name)

class Executor:
    """
    执行器，负责安全的调用工具并处理异常与重试
    """
    def __init__(self, router: ToolRouter):
        self.router = router
        
    def execute(self, name: str, arguments: str | dict) -> str:
        tool = self.router.get_tool(name)
        if not tool:
            return f"未知工具: {name}"
            
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            return tool.run_with_retry(**args)
        except Exception as e:
            logs.warning(f"Executor 执行工具 {name} 失败: {e}")
            return f"工具参数解析或执行失败: {e}"

class Planner:
    """
    LLM 决策层，负责调用模型并决策下一步行为
    """
    def __init__(self, router: ToolRouter):
        self.router = router
        
    def decide(self, messages: list[dict]) -> dict:
        """
        调用 LLM，决定下一步是使用工具（ACT）还是直接回答。
        """
        schemas = self.router.get_schema_list()
        response = call_llm(messages, tools=schemas)
        return response
        
    def stream_answer(self, messages: list[dict]) -> Generator[dict, None, None]:
        """
        调用 LLM 进行流式回答。
        """
        schemas = self.router.get_schema_list()
        for chunk in call_llm_stream(messages, tools=schemas):
            yield chunk
