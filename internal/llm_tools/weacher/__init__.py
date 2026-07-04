from __future__ import annotations

"""
天气查询工具 — 调用和风天气 (QWeather) API
"""

import json
import httpx

from config.api_cfg import QWEATHER_KEY, QWEATHER_BASE_URL
from internal.llm_tools.base import BaseTool
from tools import logs
from tools.errs import msg_error

# 城市查询使用 /geo/v2/city/lookup
_GEO_URL = f"{QWEATHER_BASE_URL}/geo/v2/city/lookup"

def _lookup_city(city_name: str) -> str | None:
    """根据城市名查询 Location ID"""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                _GEO_URL,
                params={"location": city_name, "key": QWEATHER_KEY}
            )
            data = resp.json()
            if data.get("code") == "200" and data.get("location"):
                loc = data["location"][0]
                logs.info(f"城市查询: {city_name} → {loc['name']} (ID: {loc['id']})")
                return loc["id"]
            else:
                logs.warning(f"城市查询失败: {data}")
                return None
    except Exception as e:
        logs.warning(f"城市查询异常: {e}")
        return None


class WeatherTool(BaseTool):
    name = "get_weather"
    retry = 1
    schema = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息，包括温度、湿度、风向等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称（中文），如 '北京'、'上海'、'广州'",
                    },
                },
                "required": ["city"],
            },
        },
    }

    def execute(self, city: str, **kwargs) -> str:
        """
        查询指定城市的实时天气。
        """
        try:
            # 1. 城市名 → Location ID
            location_id = _lookup_city(city)
            if not location_id:
                return f"未找到城市: {city}"

            # 2. 查询实时天气
            weather_url = f"{QWEATHER_BASE_URL}/v7/weather/now"
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    weather_url,
                    params={"location": location_id, "key": QWEATHER_KEY}
                )
                data = resp.json()

                if data.get("code") == "200" and data.get("now"):
                    now = data["now"]
                    result = (
                        f"🌤 {city} 实时天气:\n"
                        f"  天气: {now.get('text', '未知')}\n"
                        f"  温度: {now.get('temp', '?')}°C\n"
                        f"  体感温度: {now.get('feelsLike', '?')}°C\n"
                        f"  湿度: {now.get('humidity', '?')}%\n"
                        f"  风向: {now.get('windDir', '?')} {now.get('windScale', '?')}级\n"
                        f"  风速: {now.get('windSpeed', '?')}km/h\n"
                        f"  能见度: {now.get('vis', '?')}km\n"
                        f"  观测时间: {now.get('obsTime', '?')}"
                    )
                    return result
                else:
                    raise RuntimeError(f"天气查询失败: {data.get('code', '未知错误')}")

        except Exception as e:
            raise RuntimeError(f"天气查询出错: {e}")
