# XerpeX ERP System - Development Guide

This guide provides information about the project's architecture, coding standards, and contribution guidelines for developers working on the XerpeX ERP system.

## Project Architecture

The XerpeX ERP system follows the MVC (Model-View-Controller) design pattern adapted for FastAPI:

- **Models**: Database models representing the data structure
- **Schemas**: Pydantic schemas for request/response validation (equivalent to Views in traditional MVC)
- **Controllers**: API route controllers handling HTTP requests
- **Services**: Business logic services

### Directory Structure

```
app/
├── controllers/     # API route controllers
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   ├── villa.py
│   ├── booking.py
│   ├── payment.py
│   └── report.py
├── models/          # Database models
│   ├── __init__.py
│   ├── user.py
│   ├── villa.py
│   ├── booking.py
│   └── payment.py
├── schemas/         # Pydantic schemas
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   ├── villa.py
│   ├── booking.py
│   ├── payment.py
│   └── report.py
├── services/        # Business logic services
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   ├── villa.py
│   ├── booking.py
│   ├── payment.py
│   └── report.py
├── tests/           # Unit tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_user.py
│   ├── test_villa.py
│   ├── test_booking.py
│   ├── test_payment.py
│   └── test_report.py
├── utils/           # Utility functions
│   ├── __init__.py
│   ├── security.py
│   └── helpers.py
├── __init__.py
├── config.py        # Application configuration
├── database.py      # Database connection setup
└── main.py          # Main application entry point
```

### Data Flow

1. HTTP request comes in and is routed to a controller
2. Controller validates the request data using Pydantic schemas
3. Controller calls the appropriate service method
4. Service performs business logic, interacting with models as needed
5. Service returns data to the controller
6. Controller formats the response using Pydantic schemas and returns it

## Coding Standards

### Python Style Guide

This project follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code.

Key points:
- Use 4 spaces for indentation
- Maximum line length of 88 characters (using Black formatter)
- Use snake_case for variables, functions, and methods
- Use PascalCase for classes
- Use UPPER_CASE for constants

### Imports

Organize imports in the following order:
1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports

Example:
```python
# Standard library imports
import os
import json
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local application imports
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
```

### Docstrings

Use Google-style docstrings for functions and classes:

```python
def get_user_by_id(user_id: int, db: Session) -> User:
    """
    Get a user by ID.
    
    Args:
        user_id: The ID of the user to retrieve
        db: Database session
        
    Returns:
        User object if found
        
    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Error Handling

Use FastAPI's HTTPException for API errors:

```python
from fastapi import HTTPException

if not user:
    raise HTTPException(status_code=404, detail="User not found")
```

For internal errors, use custom exceptions:

```python
class PaymentProcessingError(Exception):
    """Raised when payment processing fails."""
    pass
```

### Database Queries

- Use SQLAlchemy ORM for database queries
- Create reusable query functions in services
- Handle database errors appropriately

Example:
```python
def get_villas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Villa).offset(skip).limit(limit).all()
```

## Development Workflow

### Setting Up Development Environment

1. Follow the setup instructions in the SETUP_GUIDE.md
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

### Code Formatting and Linting

This project uses:
- [Black](https://black.readthedocs.io/) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [flake8](https://flake8.pycqa.org/) for linting

Format your code before committing:
```bash
black app
isort app
flake8 app
```

### Pre-commit Hooks

Set up pre-commit hooks to automatically format and lint code:
```bash
pip install pre-commit
pre-commit install
```

### Testing

Write tests for all new features and bug fixes:
```bash
pytest app/tests/
```

For test coverage:
```bash
pytest --cov=app
```

### Git Workflow

1. Create a new branch for each feature or bug fix:
   ```bash
   git checkout -b feature/feature-name
   ```
   or
   ```bash
   git checkout -b fix/bug-name
   ```

2. Make your changes and commit them with descriptive messages:
   ```bash
   git commit -m "Add feature: description of the feature"
   ```

3. Push your branch and create a pull request:
   ```bash
   git push origin feature/feature-name
   ```

4. Ensure all tests pass before merging

## Adding New Features

### Adding a New Model

1. Create a new model file in `app/models/`
2. Define the SQLAlchemy model class
3. Add relationships to other models if needed
4. Create a migration using Alembic:
   ```bash
   alembic revision --autogenerate -m "Add new model"
   ```
5. Apply the migration:
   ```bash
   alembic upgrade head
   ```

Example:
```python
# app/models/amenity.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

class Amenity(Base):
    __tablename__ = "amenities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    villa_id = Column(Integer, ForeignKey("villas.id"))
    
    villa = relationship("Villa", back_populates="amenities")
```

### Adding a New Schema

1. Create a new schema file in `app/schemas/` or add to an existing one
2. Define Pydantic models for request and response

Example:
```python
# app/schemas/amenity.py
from pydantic import BaseModel

class AmenityBase(BaseModel):
    name: str
    description: str = None

class AmenityCreate(AmenityBase):
    villa_id: int

class AmenityUpdate(AmenityBase):
    name: str = None
    villa_id: int = None

class AmenityResponse(AmenityBase):
    id: int
    villa_id: int
    
    class Config:
        orm_mode = True
```

### Adding a New Service

1. Create a new service file in `app/services/` or add to an existing one
2. Implement business logic methods

Example:
```python
# app/services/amenity.py
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.amenity import Amenity
from app.schemas.amenity import AmenityCreate, AmenityUpdate

def get_amenities(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Amenity).offset(skip).limit(limit).all()

def get_amenity_by_id(db: Session, amenity_id: int):
    amenity = db.query(Amenity).filter(Amenity.id == amenity_id).first()
    if not amenity:
        raise HTTPException(status_code=404, detail="Amenity not found")
    return amenity

def create_amenity(db: Session, amenity: AmenityCreate):
    db_amenity = Amenity(**amenity.dict())
    db.add(db_amenity)
    db.commit()
    db.refresh(db_amenity)
    return db_amenity

def update_amenity(db: Session, amenity_id: int, amenity: AmenityUpdate):
    db_amenity = get_amenity_by_id(db, amenity_id)
    
    update_data = amenity.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_amenity, key, value)
    
    db.commit()
    db.refresh(db_amenity)
    return db_amenity

def delete_amenity(db: Session, amenity_id: int):
    db_amenity = get_amenity_by_id(db, amenity_id)
    db.delete(db_amenity)
    db.commit()
    return {"message": "Amenity deleted successfully"}
```

### Adding a New Controller

1. Create a new controller file in `app/controllers/` or add to an existing one
2. Define API routes using FastAPI's APIRouter
3. Register the router in `app/main.py`

Example:
```python
# app/controllers/amenity.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.amenity import AmenityCreate, AmenityResponse, AmenityUpdate
from app.services import amenity as amenity_service
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/api/v1/amenities", tags=["amenities"])

@router.get("/", response_model=List[AmenityResponse])
def get_amenities(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    return amenity_service.get_amenities(db, skip, limit)

@router.get("/{amenity_id}", response_model=AmenityResponse)
def get_amenity(
    amenity_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    return amenity_service.get_amenity_by_id(db, amenity_id)

@router.post("/", response_model=AmenityResponse)
def create_amenity(
    amenity: AmenityCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    return amenity_service.create_amenity(db, amenity)

@router.put("/{amenity_id}", response_model=AmenityResponse)
def update_amenity(
    amenity_id: int, 
    amenity: AmenityUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    return amenity_service.update_amenity(db, amenity_id, amenity)

@router.delete("/{amenity_id}")
def delete_amenity(
    amenity_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    return amenity_service.delete_amenity(db, amenity_id)
```

Then register the router in `app/main.py`:
```python
from app.controllers import amenity

app.include_router(amenity.router)
```

### Adding Tests

1. Create a new test file in `app/tests/`
2. Write tests using pytest

Example:
```python
# app/tests/test_amenity.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.amenity import Amenity
from app.services import amenity as amenity_service
from app.tests.utils.utils import create_test_amenity, create_test_user, get_auth_header

client = TestClient(app)

def test_create_amenity(db: Session):
    user = create_test_user(db)
    auth_header = get_auth_header(user)
    
    data = {
        "name": "Test Amenity",
        "description": "Test Description",
        "villa_id": 1
    }
    
    response = client.post("/api/v1/amenities/", json=data, headers=auth_header)
    assert response.status_code == 200
    
    content = response.json()
    assert content["name"] == data["name"]
    assert content["description"] == data["description"]
    assert content["villa_id"] == data["villa_id"]
    assert "id" in content
    
    # Clean up
    db.query(Amenity).filter(Amenity.id == content["id"]).delete()
    db.commit()
```

## Troubleshooting Common Issues

### Database Migrations

If you encounter issues with migrations:

1. Check the alembic version table:
   ```sql
   SELECT * FROM alembic_version;
   ```

2. If needed, manually set the version:
   ```sql
   DELETE FROM alembic_version;
   INSERT INTO alembic_version (version_num) VALUES ('your_target_revision');
   ```

### Authentication Issues

If you encounter JWT authentication issues:

1. Check that the SECRET_KEY is consistent
2. Verify token expiration settings
3. Check that the token is being passed correctly in the Authorization header

### Performance Issues

If you encounter performance issues:

1. Add database indexes for frequently queried fields
2. Optimize SQLAlchemy queries (use `.first()` instead of `.all()[0]`, etc.)
3. Consider adding caching for frequently accessed data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

Please ensure your code follows the project's coding standards and includes appropriate tests.

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Pytest Documentation](https://docs.pytest.org/)