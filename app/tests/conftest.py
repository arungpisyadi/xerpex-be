"""
Test configuration for the XerpeX ERP System
"""
import os
from typing import Generator, Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base, get_db
from app.main import app
from app.utils.security import create_access_token
from app.models.user import User


# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test
    """
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Create a new session for testing
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop the database tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with a database session
    """
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Reset the dependency override
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def test_user(db: Session) -> Dict[str, Any]:
    """
    Create a test user
    """
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": user.role == 'admin'
    }


@pytest.fixture(scope="function")
def test_admin(db: Session) -> Dict[str, Any]:
    """
    Create a test admin user
    """
    admin = User(
        username="testadmin",
        email="admin@example.com",
        full_name="Test Admin",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        is_active=True,
        role='admin'
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return {
        "id": admin.id,
        "username": admin.username,
        "email": admin.email,
        "full_name": admin.full_name,
        "is_admin": admin.role == 'admin'
    }


@pytest.fixture(scope="function")
def user_token(test_user: Dict[str, Any]) -> str:
    """
    Create a JWT token for the test user
    """
    return create_access_token(
        subject=test_user["username"]
    )


@pytest.fixture(scope="function")
def admin_token(test_admin: Dict[str, Any]) -> str:
    """
    Create a JWT token for the test admin
    """
    return create_access_token(
        subject=test_admin["username"]
    )


@pytest.fixture(scope="function")
def user_headers(user_token: str) -> Dict[str, str]:
    """
    Create headers with the user token
    """
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_token: str) -> Dict[str, str]:
    """
    Create headers with the admin token
    """
    return {"Authorization": f"Bearer {admin_token}"}