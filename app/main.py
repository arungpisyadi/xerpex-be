"""
Main application entry point for the XerpeX ERP System
"""
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.controllers import auth, user, villa, booking, payment, report
from app.controllers import settings as app_settings

# Set up logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(villa.router, prefix=settings.API_V1_STR)
app.include_router(booking.router, prefix=settings.API_V1_STR)
app.include_router(payment.router, prefix=settings.API_V1_STR)
app.include_router(report.router, prefix=settings.API_V1_STR)
app.include_router(app_settings.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to XerpeX ERP System API"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy"}

@app.get("/test-connection")
async def test_connection():
    """Simple endpoint to test connectivity without database access"""
    return {
        "status": "connected",
        "timestamp": str(datetime.now()),
        "message": "Connection successful"
    }


@app.get("/health/db")
async def db_health_check():
    """Database health check endpoint"""
    from sqlalchemy import text
    from app.database import get_db
    import time
    
    start_time = time.time()
    try:
        # Get database session
        db = next(get_db())
        
        # Execute simple query with timeout
        result = db.execute(text("SELECT 1")).fetchone()
        
        # Calculate response time
        response_time = time.time() - start_time
        
        if result and result[0] == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "message": "Database connection successful",
                "response_time_seconds": response_time
            }
        else:
            return {
                "status": "unhealthy",
                "database": "error",
                "message": "Database returned unexpected result",
                "response_time_seconds": response_time
            }
    except Exception as e:
        # Calculate response time even for errors
        response_time = time.time() - start_time
        return {
            "status": "unhealthy",
            "database": "error",
            "message": f"Database connection failed: {str(e)}",
            "response_time_seconds": response_time
        }

@app.get("/test-db-tables")
async def test_db_tables():
    """Test database tables endpoint"""
    from sqlalchemy import text, inspect
    from app.database import get_db, engine
    import time
    
    start_time = time.time()
    try:
        # Get database session
        db = next(get_db())
        
        # Get list of tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Test query on user table if it exists
        user_count = None
        if 'user' in tables:
            result = db.execute(text("SELECT COUNT(*) FROM user")).fetchone()
            user_count = result[0] if result else None
        
        # Calculate response time
        response_time = time.time() - start_time
        
        return {
            "status": "success",
            "tables": tables,
            "user_count": user_count,
            "response_time_seconds": response_time
        }
    except Exception as e:
        # Calculate response time even for errors
        response_time = time.time() - start_time
        return {
            "status": "error",
            "message": f"Database test failed: {str(e)}",
            "response_time_seconds": response_time
        }



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for HTTP exceptions"""
    # Log the exception
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    # Return the original response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to capture all unhandled exceptions"""
    # Log the exception
    logger.error(f"Global Exception: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )