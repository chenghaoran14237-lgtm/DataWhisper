from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 关键：允许从 .env 读取；忽略多余字段；大小写不敏感
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------
    # 基础信息
    # ----------------------------
    env: str = Field(default="dev", alias="ENV")
    app_name: str = Field(default="DataWhisper", alias="APP_NAME")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    # ----------------------------
    # 对话上下文 / summary（你原本那套）
    # ----------------------------
    max_context_tokens: int = Field(default=3000, alias="MAX_CONTEXT_TOKENS")
    summary_trigger_tokens: int = Field(default=1000, alias="SUMMARY_TRIGGER_TOKENS")
    summary_max_chars: int = Field(default=1500, alias="SUMMARY_MAX_CHARS")
    context_recent_limit: int = Field(default=20, alias="CONTEXT_RECENT_LIMIT")

    # ----------------------------
    # 文件相关
    # ----------------------------
    max_upload_mb: int = Field(default=10, alias="MAX_UPLOAD_MB")
    data_dir: str = Field(default="./data", alias="DATA_DIR")

    # ----------------------------
    # 数据库相关（MySQL）
    # ----------------------------
    database_url: str = Field(
        default="mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper?charset=utf8mb4",
        alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    # ----------------------------
    # LLM 相关
    # ----------------------------
    llm_provider: str = Field(default="fake", alias="LLM_PROVIDER")  # fake / openai

    # OpenAI / OpenAI-compatible（Gemini 兼容层也走这里）
    openai_api_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_timeout_s: int = Field(default=30, alias="OPENAI_TIMEOUT_S")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=800, alias="OPENAI_MAX_TOKENS")

    # （可选）你之前分 chat/summary 不同模型的写法：保留也行
    # 如果你代码里没用到，可以不写；写了也不会影响
    openai_model_chat: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL_CHAT")
    openai_model_summary: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL_SUMMARY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
