from __future__ import annotations

"""
网络搜索工具 — 调用阿里 IQS 联网搜索 API
"""

from Tea.exceptions import TeaException
from alibabacloud_iqs20241111 import models
from alibabacloud_iqs20241111.client import Client
from alibabacloud_tea_openapi import models as open_api_models

from config.api_cfg import ALI_IQS_AK, ALI_IQS_SK
from internal.llm_tools.base import BaseTool
from tools import logs
from tools.errs import msg_error


def _create_client() -> Client:
    """创建并初始化阿里 IQS 客户端"""
    config = open_api_models.Config(
        access_key_id=ALI_IQS_AK,
        access_key_secret=ALI_IQS_SK
    )
    config.endpoint = 'iqs.cn-zhangjiakou.aliyuncs.com'
    return Client(config)


class SearchTool(BaseTool):
    name = "web_search"
    retry = 1
    schema = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网获取最新信息。当你需要查找最新资讯、事实、数据时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                },
                "required": ["query"],
            },
        },
    }

    def execute(self, query: str, **kwargs) -> str:
        """
        调用阿里 IQS 搜索 API，返回搜索结果摘要。
        """
        try:
            # 处理未填入 AK/SK 的情况
            if not ALI_IQS_AK or ALI_IQS_AK.startswith("请填入你的"):
                return "搜索失败: 未配置阿里 IQS AccessKey，请在 config/api_cfg.py 中填写 ALI_IQS_AK 和 ALI_IQS_SK。"

            client = _create_client()
            run_instances_request = models.UnifiedSearchRequest(
                body=models.UnifiedSearchInput(
                    query=query,
                    time_range='NoLimit',
                    contents=models.RequestContents(
                        summary=True,
                        main_text=False,
                    )
                )
            )
            
            response = client.unified_search(run_instances_request)
            
            # 提取搜索结果并拼接
            if response.body.page_items and len(response.body.page_items) > 0:
                summaries = []
                for item in response.body.page_items[:5]:
                    title = item.title or "无标题"
                    snippet = item.snippet or item.summary or ""
                    summaries.append(f"【{title}】{snippet}")
                return "\n".join(summaries)
            else:
                return "搜索成功，但未找到相关内容。"

        except TeaException as e:
            code = e.code
            request_id = e.data.get("requestId") if hasattr(e, 'data') and isinstance(e.data, dict) else ""
            message = e.data.get("message") if hasattr(e, 'data') and isinstance(e.data, dict) else e.message
            raise RuntimeError(f"搜索出错 (API Error): {message}")
        except Exception as e:
            raise RuntimeError(f"搜索内部出错: {e}")
