"""
Configuration settings for the XerpeX ERP System
"""
import os
import json
from typing import Optional, List
from pydantic import AnyUrl, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "XerpeX ERP System"
    
    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database settings
    MYSQL_SERVER: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str
    MYSQL_PORT: str = "3306"
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get the database URI"""
        # When server is localhost, explicitly use TCP by replacing with 127.0.0.1
        # This prevents MySQLdb from trying to use a Unix socket
        server = "127.0.0.1" if self.MYSQL_SERVER.lower() == "localhost" else self.MYSQL_SERVER
        return f"mysql+mysqldb://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{server}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return ["*"]
        return v
    
    # Sentry settings (permanently disabled)
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0  # 0% of transactions
    SENTRY_ENABLE: bool = Field(default=False, description="Permanently disabled")
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create settings instance
settings = Settings()