"""
Configuration settings for the XerpeX ERP System
"""
import os
from typing import Optional
from pydantic import AnyUrl, Field
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
        return f"mysql+mysqldb://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # Sentry settings
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0  # 100% of transactions
    SENTRY_ENABLE: bool = Field(default=False)
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create settings instance
settings = Settings()