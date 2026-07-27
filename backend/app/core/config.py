from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ai-cs-agent"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/chat.db"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    log_level: str = "INFO"
    handover_keywords: str = "人工,转人工,客服,真人,投诉"
    handover_timeout: int = 3600

    model_config = {"env_prefix": "CS_", "env_file": ".env"}


settings = Settings()
