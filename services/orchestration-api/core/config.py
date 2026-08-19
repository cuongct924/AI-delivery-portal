"""Centralized configuration — read from environment variables (.env at the repo root)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    mlflow_tracking_uri: str = "http://localhost:5000"

    auth_enabled: bool = False
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "ai-delivery-portal"
    keycloak_client_id: str = "orchestration-api"

    litellm_gateway_url: str = "http://localhost:4000"
    litellm_master_key: str = ""
    qdrant_url: str = "http://localhost:6333"

    class Config:
        env_file = "../../.env"


settings = Settings()
