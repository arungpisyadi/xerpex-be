"""
Dummy Sentry utility functions (all Sentry functionality disabled)
"""
import logging
from typing import Any, Callable, Dict, Optional, Union, TypeVar

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# Type variables for function signatures
F = TypeVar('F', bound=Callable[..., Any])

def capture_exception(*args, **kwargs) -> None:
    """Dummy function that does nothing"""
    logger.error(f"Error captured (Sentry disabled): {args}")
    return None

def capture_message(*args, **kwargs) -> None:
    """Dummy function that does nothing"""
    logger.info(f"Message captured (Sentry disabled): {args}")
    return None

def get_request_info(request: Request) -> Dict[str, Any]:
    """Dummy function that returns minimal request info"""
    return {
        "url": str(request.url),
        "method": request.method,
    }

def log_exception_with_request(*args, **kwargs) -> None:
    """Dummy function that does nothing"""
    logger.error(f"Exception with request (Sentry disabled): {args}")
    return None

def sentry_monitored(*args, **kwargs) -> Callable[[F], F]:
    """Dummy decorator that just returns the original function"""
    def decorator(func: F) -> F:
        return func
    return decorator

def sentry_monitored_controller(func: F) -> F:
    """Dummy decorator that just returns the original function"""
    return func

def sentry_monitored_service(func: F) -> F:
    """Dummy decorator that just returns the original function"""
    return func

def sentry_monitored_util(func: F) -> F:
    """Dummy decorator that just returns the original function"""
    return func

def set_user_context(*args, **kwargs) -> None:
    """Dummy function that does nothing"""
    return None

def clear_user_context() -> None:
    """Dummy function that does nothing"""
    return None