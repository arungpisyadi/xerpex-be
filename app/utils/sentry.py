"""
Utility functions for Sentry error logging
"""
import functools
import inspect
import logging
import traceback
from typing import Any, Callable, Dict, Optional, Union, TypeVar, cast

import sentry_sdk
from fastapi import Request, HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.config import settings

logger = logging.getLogger(__name__)


def capture_exception(
    exception: Union[Exception, HTTPException],
    context: Optional[Dict[str, Any]] = None,
    level: str = "error",
    request: Optional[Request] = None,
) -> None:
    """
    Capture an exception and send it to Sentry if enabled
    
    Args:
        exception: The exception to capture
        context: Additional context data to include with the exception
        level: The severity level (error, warning, info, etc.)
    """
    if not settings.SENTRY_ENABLE:
        # Log locally if Sentry is not enabled
        logger.error(
            f"Exception: {str(exception)}\nTraceback: {traceback.format_exc()}"
        )
        return

    # Process request information if provided
    if request and not context:
        context = {"request": get_request_info(request)}
    elif request and context and "request" not in context:
        context["request"] = get_request_info(request)
    
    # Handle HTTPException specially
    if isinstance(exception, HTTPException):
        status_code = exception.status_code
        detail = exception.detail
        
        # Add HTTP exception details to context
        if context is None:
            context = {}
        
        context.update({
            "status_code": status_code,
            "detail": detail,
        })
        
        # For 4xx errors, log as warnings unless they're 500+
        if status_code < 500:
            capture_message(
                f"HTTP {status_code}: {detail}",
                context=context,
                level="warning"
            )
            return
    
    # Add context data if provided
    if context:
        with sentry_sdk.configure_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
    
    # Capture the exception with the specified level
    if level == "error":
        sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_message(str(exception), level=level)


def capture_message(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    level: str = "info",
    request: Optional[Request] = None,
) -> None:
    """
    Capture a message and send it to Sentry if enabled
    
    Args:
        message: The message to capture
        context: Additional context data to include with the message
        level: The severity level (error, warning, info, etc.)
    """
    if not settings.SENTRY_ENABLE:
        # Log locally if Sentry is not enabled
        logger_method = getattr(logger, level, logger.info)
        logger_method(message)
        return

    # Process request information if provided
    if request and not context:
        context = {"request": get_request_info(request)}
    elif request and context and "request" not in context:
        context["request"] = get_request_info(request)
    
    # Add context data if provided
    if context:
        with sentry_sdk.configure_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
    
    # Capture the message with the specified level
    sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: Optional[str] = None) -> None:
    """
    Set user context for Sentry events
    
    Args:
        user_id: The user ID
        email: The user email (optional)
    """
    if not settings.SENTRY_ENABLE:
        return

    user_data = {"id": user_id}
    if email:
        user_data["email"] = email
    
    sentry_sdk.set_user(user_data)


def clear_user_context() -> None:
    """Clear user context for Sentry events"""
    if not settings.SENTRY_ENABLE:
        return
    
    sentry_sdk.set_user(None)


def get_request_info(request: Request) -> Dict[str, Any]:
    """
    Extract useful information from a FastAPI request
    
    Args:
        request: The FastAPI request object
        
    Returns:
        Dictionary with request information
    """
    # Basic request info
    info = {
        "url": str(request.url),
        "method": request.method,
        "headers": {k: v for k, v in request.headers.items() if k.lower() not in ["authorization", "cookie"]},
        "client_host": request.client.host if request.client else None,
        "path_params": request.path_params,
        "query_params": dict(request.query_params),
    }
    
    # Add user info if available in session
    try:
        if hasattr(request, "state") and hasattr(request.state, "user"):
            user = request.state.user
            if user:
                info["user"] = {
                    "id": getattr(user, "id", None),
                    "email": getattr(user, "email", None),
                }
    except Exception:
        # Ignore errors when trying to get user info
        pass
    
    return info


def log_exception_with_request(
    exception: Exception,
    request: Request,
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
    additional_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Convenience function to log an exception with request information
    
    Args:
        exception: The exception to log
        request: The FastAPI request
        status_code: HTTP status code
        additional_context: Any additional context to include
    """
    context = {"request": get_request_info(request), "status_code": status_code}
    
    if additional_context:
        context.update(additional_context)
    
    capture_exception(exception, context=context)


# Type variables for function signatures
F = TypeVar('F', bound=Callable[..., Any])
R = TypeVar('R')


def sentry_monitored(
    module_name: Optional[str] = None,
    capture_args: bool = True,
    capture_return: bool = False,
    level: str = "error"
) -> Callable[[F], F]:
    """
    Decorator to monitor functions with Sentry
    
    Args:
        module_name: Optional module name to use in logs
        capture_args: Whether to capture function arguments
        capture_return: Whether to capture function return value
        level: Log level for non-exception events
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        # Get function metadata
        func_name = func.__name__
        module = module_name or func.__module__
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Prepare context
            context: Dict[str, Any] = {
                "function": f"{module}.{func_name}",
            }
            
            # Capture arguments if requested
            if capture_args:
                # Get function signature
                sig = inspect.signature(func)
                
                # Map positional args to parameter names
                param_names = list(sig.parameters.keys())
                args_dict = {}
                
                # Skip 'self' or 'cls' for instance/class methods
                start_idx = 0
                if args and param_names and param_names[0] in ('self', 'cls'):
                    start_idx = 1
                
                # Map positional args to names
                for i, arg in enumerate(args[start_idx:], start_idx):
                    if i < len(param_names):
                        # Skip request objects to avoid duplication
                        if isinstance(arg, Request):
                            args_dict[param_names[i]] = "<Request object>"
                        else:
                            try:
                                # Try to convert to dict if possible
                                if hasattr(arg, 'dict') and callable(getattr(arg, 'dict')):
                                    args_dict[param_names[i]] = arg.dict()
                                else:
                                    args_dict[param_names[i]] = str(arg)
                            except Exception:
                                args_dict[param_names[i]] = str(arg)
                
                # Add kwargs, filtering out request objects
                kwargs_dict = {}
                for k, v in kwargs.items():
                    if isinstance(v, Request):
                        kwargs_dict[k] = "<Request object>"
                    else:
                        try:
                            # Try to convert to dict if possible
                            if hasattr(v, 'dict') and callable(getattr(v, 'dict')):
                                kwargs_dict[k] = v.dict()
                            else:
                                kwargs_dict[k] = str(v)
                        except Exception:
                            kwargs_dict[k] = str(v)
                
                context["args"] = args_dict
                context["kwargs"] = kwargs_dict
            
            # Extract request object if present
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for v in kwargs.values():
                    if isinstance(v, Request):
                        request = v
                        break
            
            # Add request info if available
            if request:
                context["request"] = get_request_info(request)
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Capture return value if requested
                if capture_return and result is not None:
                    try:
                        if hasattr(result, 'dict') and callable(getattr(result, 'dict')):
                            context["result"] = result.dict()
                        else:
                            context["result"] = str(result)
                    except Exception:
                        context["result"] = str(result)
                
                return result
            except Exception as e:
                # Capture exception with context
                capture_exception(e, context=context)
                
                # Re-raise the exception
                raise
        
        return cast(F, wrapper)
    
    return decorator


def sentry_monitored_controller(func: F) -> F:
    """
    Decorator specifically for controller functions
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    return sentry_monitored(
        module_name="controllers",
        capture_args=True,
        capture_return=False
    )(func)


def sentry_monitored_service(func: F) -> F:
    """
    Decorator specifically for service functions
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    return sentry_monitored(
        module_name="services",
        capture_args=True,
        capture_return=True
    )(func)


def sentry_monitored_util(func: F) -> F:
    """
    Decorator specifically for utility functions
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    return sentry_monitored(
        module_name="utils",
        capture_args=True,
        capture_return=False
    )(func)