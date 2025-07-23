# Sentry Integration Guide

This document provides instructions on how to apply Sentry error logging to all functions in the XerpeX ERP System.

## Overview

The system has been configured to use Sentry.io for error logging. The following components have been implemented:

1. Sentry SDK configuration in `app/config.py`
2. Global exception handlers in `app/main.py`
3. Middleware for capturing request parameters
4. Utility functions for error logging in `app/utils/sentry.py`
5. Decorators for easy integration with existing functions

## Configuration

Sentry is configured via environment variables in the `.env` file:

```
SENTRY_DSN=https://your-sentry-dsn@sentry.io/your-project-id
SENTRY_ENVIRONMENT=production  # or development, staging, etc.
SENTRY_TRACES_SAMPLE_RATE=1.0  # Adjust as needed (0.0 to 1.0)
SENTRY_ENABLE=true
```

## Applying Sentry Logging to Functions

### Using Decorators

The easiest way to add Sentry logging to functions is to use the provided decorators:

#### For Controller Functions

```python
from app.utils.sentry import sentry_monitored_controller

@router.get("/endpoint")
@sentry_monitored_controller
async def my_controller_function(request: Request, ...):
    # Your code here
    pass
```

#### For Service Functions

```python
from app.utils.sentry import sentry_monitored_service

@sentry_monitored_service
def my_service_function(db: Session, ...):
    # Your code here
    pass
```

#### For Utility Functions

```python
from app.utils.sentry import sentry_monitored_util

@sentry_monitored_util
def my_utility_function(...):
    # Your code here
    pass
```

#### Custom Monitoring

For more control, you can use the base decorator:

```python
from app.utils.sentry import sentry_monitored

@sentry_monitored(
    module_name="custom_module",
    capture_args=True,
    capture_return=True,
    level="error"
)
def my_custom_function(...):
    # Your code here
    pass
```

### Manual Logging

For cases where decorators are not suitable, you can use the utility functions directly:

```python
from app.utils.sentry import capture_exception, capture_message, log_exception_with_request

try:
    # Your code here
except Exception as e:
    # For exceptions with request context
    log_exception_with_request(e, request, additional_context={"key": "value"})
    
    # Or for exceptions without request
    capture_exception(e, context={"key": "value"})
    
    # Re-raise or handle as needed
    raise

# For logging messages
capture_message("Something happened", level="info")
```

## Implementation Strategy

To apply Sentry logging to all functions in the codebase:

1. **Controllers**: Add `@sentry_monitored_controller` to all controller functions
2. **Services**: Add `@sentry_monitored_service` to all service functions
3. **Utils**: Add `@sentry_monitored_util` to all utility functions

### Example Implementation

See the following files for examples:

- `app/controllers/settings.py` - Controller functions with Sentry decorators
- `app/services/settings.py` - Service functions with Sentry decorators

## Benefits

- Automatic capture of function arguments and context
- Automatic capture of request information when available
- Consistent error logging across the application
- Detailed error reports in Sentry dashboard
- Minimal code changes required

## Notes

- The decorators automatically handle exceptions and re-raise them after logging
- HTTP exceptions with status codes < 500 are logged as warnings
- HTTP exceptions with status codes >= 500 are logged as errors
- Request parameters and body content are automatically captured
- User information is included when available