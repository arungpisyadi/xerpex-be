"""
Main application entry point for the XerpeX ERP System
"""
import json
import os
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.controllers import auth, user, villa, booking, payment, report, salesmen, survey, package, sales
from app.controllers import customer, tax, quote, invoice, kpi
from app.controllers import settings as app_settings
from app.controllers import target
from app.database import get_db
from app.services.target import TargetService
from app.services.survey_background_tasks import retry_failed_email_jobs, cleanup_old_survey_jobs
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

# Initialize APScheduler
scheduler = AsyncIOScheduler()

# Define the monthly target recalculation job
async def monthly_target_recalculation():
    """Scheduled job to recalculate monthly targets for all sales users"""
    try:
        # Get database session
        db = next(get_db())

        # Create target service and run recalculation
        target_service = TargetService(db)
        target_service.recalculate_monthly_targets_for_all_users()

        print("Monthly target recalculation job completed successfully")
    except Exception as e:
        print(f"Error in monthly target recalculation job: {str(e)}")
    finally:
        db.close()

# Define the email retry job
async def retry_failed_survey_emails():
    """Scheduled job to retry failed survey email notifications"""
    try:
        processed_count = await retry_failed_email_jobs(limit=50)
        if processed_count > 0:
            print(f"Retried {processed_count} failed survey email jobs")
    except Exception as e:
        print(f"Error in retry failed survey emails job: {str(e)}")

# Define the cleanup job
async def cleanup_old_survey_email_jobs():
    """Scheduled job to cleanup old survey email jobs"""
    try:
        await cleanup_old_survey_jobs(days_old=30)
        print("Cleaned up old survey email jobs")
    except Exception as e:
        print(f"Error in cleanup survey email jobs: {str(e)}")

# Add the scheduled job to run at 2:00 AM on the 1st of every month
scheduler.add_job(
    monthly_target_recalculation,
    trigger=CronTrigger(day=1, hour=2, minute=0),
    id="monthly_target_recalculation",
    name="Monthly Target Recalculation",
    replace_existing=True
)

# Add the email retry job to run every 5 minutes
scheduler.add_job(
    retry_failed_survey_emails,
    trigger=CronTrigger(minute="*/5"),
    id="retry_failed_survey_emails",
    name="Retry Failed Survey Emails",
    replace_existing=True
)

# Add the cleanup job to run daily at 3:00 AM
scheduler.add_job(
    cleanup_old_survey_email_jobs,
    trigger=CronTrigger(hour=3, minute=0),
    id="cleanup_old_survey_email_jobs",
    name="Cleanup Old Survey Email Jobs",
    replace_existing=True
)

# Set up CORS middleware for development environments
# In production, CORS is handled by Nginx
if settings.SENTRY_ENVIRONMENT in ["localhost", "development"]:
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

# Add the Sentry middleware if Sentry is enabled (disabled for testing)
# if settings.SENTRY_ENABLE:
#     app.add_middleware(SentryMiddleware)

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(sales.router, prefix=settings.API_V1_STR)
app.include_router(villa.router, prefix=settings.API_V1_STR)
app.include_router(booking.router, prefix=settings.API_V1_STR)
app.include_router(payment.router, prefix=settings.API_V1_STR)
app.include_router(report.router, prefix=settings.API_V1_STR)
app.include_router(salesmen.router, prefix=settings.API_V1_STR)
app.include_router(survey.router, prefix=settings.API_V1_STR)
app.include_router(package.router, prefix=settings.API_V1_STR)
app.include_router(app_settings.router, prefix=settings.API_V1_STR)

# Include new invoicing system routers
# print(f"DEBUG: Including customer router with prefix {settings.API_V1_STR}")
app.include_router(customer.router, prefix=settings.API_V1_STR)
app.include_router(tax.router, prefix=settings.API_V1_STR)
app.include_router(quote.router, prefix=settings.API_V1_STR)
app.include_router(invoice.router, prefix=settings.API_V1_STR)

# Include KPI router
app.include_router(kpi.router, prefix=settings.API_V1_STR)

# Include target routers
app.include_router(target.admin_router, prefix=settings.API_V1_STR)
app.include_router(target.targets_router, prefix=settings.API_V1_STR)


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


@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the application starts"""
    # Skip scheduler in testing mode
    if os.getenv("PYTEST_CURRENT_TEST") is None:
        if not scheduler.running:
            scheduler.start()
            print("APScheduler started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler when the application shuts down"""
    # Only shutdown scheduler if it was started (not in testing mode)
    if os.getenv("PYTEST_CURRENT_TEST") is None and scheduler.running:
        scheduler.shutdown()
        print("APScheduler shut down successfully")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(request: Request, path: str):
    """Catch-all route to log unmatched requests"""
    print(f"DEBUG: Unmatched request - Method: {request.method}, URL: {request.url}, Path: {path}")
    raise HTTPException(status_code=404, detail="Not found")