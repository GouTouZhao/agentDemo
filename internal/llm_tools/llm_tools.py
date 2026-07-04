from internal.llm_tools.calculater import CalculatorTool
from internal.llm_tools.research import SearchTool
from internal.llm_tools.weacher import WeatherTool
from internal.llm_tools.base import BaseTool

# 暴露所有可用工具的类
AVAILABLE_TOOLS = [
    CalculatorTool,
    SearchTool,
    WeatherTool,
]
