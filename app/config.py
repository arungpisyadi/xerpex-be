"""
Configuration settings for the XerpeX ERP System
"""
import os
import json
from typing import Annotated, Optional, List
from pydantic import AnyUrl, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # Enable app-level CORS when no reverse proxy (e.g. Nginx) adds CORS headers, such as on Coolify
    CORS_ENABLE: bool = False
    # NoDecode: let the validator below parse the raw env value instead of pydantic-settings
    BACKEND_CORS_ORIGINS: Annotated[List[str], NoDecode] = ["*"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Drop surrounding quotes, e.g. BACKEND_CORS_ORIGINS="a,b" kept literally by the platform
            v = v.strip().strip("'\"")
        if isinstance(v, str) and not v.startswith("["):
            # Use a set to remove duplicates, then convert back to list
            return list(set(i.strip().strip("'\"") for i in v.split(",") if i.strip()))
        if isinstance(v, str):
            try:
                # Parse JSON and remove duplicates
                origins = json.loads(v)
                return list(set(origins)) if isinstance(origins, list) else origins
            except json.JSONDecodeError:
                # Tolerate malformed JSON (e.g. trailing comma, single quotes) by splitting manually
                items = (i.strip().strip("'\"") for i in v.strip().strip("[]").split(","))
                return list(set(i for i in items if i))
        # If it's already a list, remove duplicates
        return list(set(v)) if isinstance(v, list) else v
    
    # Email settings
    ADMIN_EMAIL: Optional[str] = None
    SALES_ADMIN_EMAIL: Optional[str] = None
    SALES_DIRECTOR_EMAIL: Optional[str] = None
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_FROM_NAME: str = "XerpeX ERP System"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    
    # Sentry settings
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0  # 100% of transactions
    SENTRY_ENABLE: bool = Field(default=False)
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create settings instance
settings = Settings()