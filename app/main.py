"""
Main application entry point for the XerpeX ERP System
"""
import json
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.controllers import auth, user, villa, booking, payment, report, salesmen, survey
from app.controllers import settings as app_settings
from app.utils.sentry import (
    capture_exception,
    capture_message,
    get_request_info,
    log_exception_with_request
)

# Initialize Sentry if enabled
if settings.SENTRY_ENABLE and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create a middleware to log request parameters
class SentryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Collect request data
        request_info = get_request_info(request)
        
        # Try to parse request body if it's a POST/PUT/PATCH request
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    try:
                        # Try to parse as JSON
                        request_info["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        # If not JSON, store as string (truncated if too large)
                        body_str = body.decode("utf-8", errors="replace")
                        request_info["body"] = body_str[:1000] + "..." if len(body_str) > 1000 else body_str
            except Exception:
                # If we can't read the body, just continue
                pass
        
        # Add request info to Sentry scope
        with sentry_sdk.configure_scope() as scope:
            scope.set_context("request", request_info)
        
        # Process the request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # This will catch exceptions not caught by exception handlers
            capture_exception(e, context={"request": request_info})
            raise

# Add the Sentry middleware if Sentry is enabled
if settings.SENTRY_ENABLE:
    app.add_middleware(SentryMiddleware)

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(villa.router, prefix=settings.API_V1_STR)
app.include_router(booking.router, prefix=settings.API_V1_STR)
app.include_router(payment.router, prefix=settings.API_V1_STR)
app.include_router(report.router, prefix=settings.API_V1_STR)
app.include_router(salesmen.router, prefix=settings.API_V1_STR)
app.include_router(survey.router, prefix=settings.API_V1_STR)
app.include_router(app_settings.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to XerpeX ERP System API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for HTTP exceptions"""
    # Use the enhanced capture_exception which handles HTTPExceptions specially
    capture_exception(exc, request=request)
    
    # Return the original response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to capture all unhandled exceptions"""
    # Use the convenience function to log exception with request
    log_exception_with_request(exc, request)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )