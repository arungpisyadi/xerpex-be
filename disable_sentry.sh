#!/bin/bash
# Script to disable and remove all Sentry-related functions

# Set error handling
set -e
echo "Starting Sentry removal..."

# 1. Disable Sentry in config.py
echo "Disabling Sentry in config.py..."
sed -i 's/SENTRY_ENABLE: bool = Field(default=False)/SENTRY_ENABLE: bool = Field(default=False, description="Permanently disabled")/g' app/config.py

# 2. Create a dummy sentry.py file that does nothing
echo "Creating dummy sentry.py file..."
cat > app/utils/sentry.py << 'EOF'
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
EOF

# 3. Update main.py to remove Sentry initialization and middleware
echo "Updating main.py to remove Sentry initialization and middleware..."

# Create a backup of main.py
cp app/main.py app/main.py.bak

# Remove Sentry initialization
sed -i '/# Initialize Sentry if enabled/,/^$/d' app/main.py

# Remove SentryMiddleware class
sed -i '/# Create a middleware to log request parameters/,/# Add the Sentry middleware if Sentry is enabled/d' app/main.py

# Remove adding Sentry middleware
sed -i '/# Add the Sentry middleware if Sentry is enabled/,/^$/d' app/main.py

# Remove Sentry from exception handlers
sed -i 's/capture_exception(exc, request=request)/logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")/g' app/main.py
sed -i 's/log_exception_with_request(exc, request)/logger.error(f"Global Exception: {str(exc)}")/g' app/main.py

# 4. Add proper imports for logger
sed -i '4 a import logging' app/main.py
sed -i '5 a logger = logging.getLogger(__name__)' app/main.py

# 5. Remove sentry_sdk import
sed -i '/import sentry_sdk/d' app/main.py

# 6. Create a script to restart the application
echo "Creating restart script..."
cat > restart_without_sentry.sh << 'EOF'
#!/bin/bash
# Script to restart the application without Sentry

# Set error handling
set -e
echo "Restarting application without Sentry..."

# Restart the application
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl restart xerpex || echo "Failed to restart with supervisor."
fi

if command -v systemctl &> /dev/null; then
    sudo systemctl restart xerpex || echo "Failed to restart with systemd."
fi

# Wait for the application to start
echo "Waiting for the application to start..."
sleep 10

# Test the application
echo "Testing the application..."
curl -s http://localhost:8000/health

echo "Application restarted without Sentry!"
EOF

chmod +x restart_without_sentry.sh

echo "Sentry has been disabled and removed from the application."
echo "Run ./restart_without_sentry.sh to restart the application without Sentry."