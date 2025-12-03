from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


class LLMProvider:
    async def generate(self, *, system: str, user: str, tool_result: str) -> str:
        raise NotImplementedError


@dataclass
class FakeLLMProvider(LLMProvider):
    async def generate(self, *, system: str, user: str, tool_result: str) -> str:
        # 纯模板：可预测、便于测试
        return (
            "我先按你的问题做了可复现的表格计算（见下方结果），再给出解释：\n\n"
            f"【你的问题】\n{user}\n\n"
            f"【计算结果】\n{tool_result}\n\n"
            "【解释】\n"
            "1) 上面“计算结果”是直接由 pandas 从表格算出来的。\n"
            "2) 如果你希望按某一列分组（比如按月份/地区），告诉我分组列名即可。\n"
            "3) 也可以问：最大/最小/均值/总和/TopN/趋势，我会给你对应统计。\n"
        )


class OpenAIChatProvider(LLMProvider):
    """
    使用 OpenAI Chat Completions: POST /v1/chat/completions
    文档：https://platform.openai.com/docs/api-reference/chat :contentReference[oaicite:1]{index=1}
    """

    def __init__(self) -> None:
        s = get_settings()

        # 这些字段需要你在 Settings 里定义（见下方第2部分）
        api_key = getattr(s, "openai_api_key", None)
        if api_key is None:
            raise RuntimeError("LLM_PROVIDER=openai 但 Settings 里没有 openai_api_key 字段（请按文档补齐 Settings）")

        # pydantic SecretStr 兼容 + 普通 str 兼容
        self.api_key = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else str(api_key)
        if not self.api_key:
            raise RuntimeError("LLM_PROVIDER=openai 但未设置 OPENAI_API_KEY")

        self.base_url = (getattr(s, "openai_base_url", "https://api.openai.com/v1") or "https://api.openai.com/v1").rstrip(
            "/"
        )
        self.model = getattr(s, "openai_model", "gpt-4o-mini")
        self.timeout_s = int(getattr(s, "openai_timeout_s", 30))
        self.temperature = float(getattr(s, "openai_temperature", 0.2))
        self.max_tokens = int(getattr(s, "openai_max_tokens", 800))

    async def generate(self, *, system: str, user: str, tool_result: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        # 关键：强制“基于工具输出回答”，避免模型胡编
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {
                "role": "assistant",
                "content": (
                    "你必须基于下面【工具输出】回答，不要编造；如果工具输出不足以回答，请明确说明还缺什么信息。\n\n"
                    f"【工具输出】\n{tool_result}"
                ),
            },
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # 简单重试：针对 429 / 5xx
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)

                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)

                resp.raise_for_status()
                data = resp.json()
                content = (data["choices"][0]["message"]["content"] or "").strip()
                return content or "（模型没有返回内容）"

            except Exception:
                if attempt == 2:
                    # 最后一次失败：抛出，让上层看到真实错误（便于排查）
                    raise
                await _backoff_sleep(attempt)


async def _backoff_sleep(attempt: int) -> None:
    # 0: ~0.6s, 1: ~1.2s, 2: ~2.4s (+ jitter)
    base = 0.6 * (2**attempt)
    jitter = random.random() * 0.2
    await asyncio.sleep(base + jitter)


def get_llm_provider() -> LLMProvider:
    s = get_settings()
    p = (getattr(s, "llm_provider", None) or "fake").lower()

    if p == "openai":
        return OpenAIChatProvider()

    # 默认 fake（用于测试/离线）
    return FakeLLMProvider()
