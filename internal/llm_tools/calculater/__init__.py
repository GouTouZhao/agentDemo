"""
多项式计算器工具 — 安全地计算数学表达式
"""

import ast
import math
import operator

from internal.llm_tools.base import BaseTool
from tools import logs
from tools.errs import new_error

# 允许的安全运算符
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# 允许的安全数学函数
_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    """递归安全求值 AST 节点"""
    if isinstance(node, ast.Constant):  # 数字常量
        if isinstance(node.value, (int, float)):
            return node.value
        raise new_error(f"不支持的常量类型: {type(node.value)}")

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            return _SAFE_OPERATORS[op_type](_safe_eval(node.operand))
        raise new_error(f"不支持的一元运算: {op_type.__name__}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            left = _safe_eval(node.left)
            right = _safe_eval(node.right)
            return _SAFE_OPERATORS[op_type](left, right)
        raise new_error(f"不支持的二元运算: {op_type.__name__}")

    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCTIONS:
            func = _SAFE_FUNCTIONS[node.func.id]
            args = [_safe_eval(arg) for arg in node.args]
            return func(*args)
        raise new_error(f"不允许的函数调用: {ast.dump(node.func)}")

    elif isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[node.id]
        raise new_error(f"未知变量: {node.id}")

    else:
        raise new_error(f"不支持的表达式类型: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    retry = 0
    schema = {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式。支持加减乘除、幂运算、取模、sqrt、sin、cos、tan、log 等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，如 '2**10 + sqrt(144)'",
                    },
                },
                "required": ["expression"],
            },
        },
    }

    def execute(self, expression: str, **kwargs) -> str:
        """
        安全计算数学表达式。
        """
        try:
            tree = ast.parse(expression, mode="eval")
            result = _safe_eval(tree.body)
            logs.info(f"计算结果: {result}")
            return str(result)
        except Exception as e:
            raise new_error(f"计算错误: {e}")
