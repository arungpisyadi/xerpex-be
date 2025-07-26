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

# If neither supervisor nor systemd is available, try to restart manually
if ! command -v supervisorctl &> /dev/null && ! command -v systemctl &> /dev/null; then
    echo "No service manager found. Trying to restart manually..."
    
    # Kill any running uvicorn processes
    pkill -f "uvicorn app.main:app" || echo "No running uvicorn processes found."
    
    # Start the application in the background
    cd /opt/xerpex || cd .
    source venv/bin/activate || echo "Virtual environment not found."
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
    
    echo "Application started with PID: $!"
fi

# Wait for the application to start
echo "Waiting for the application to start..."
sleep 10

# Test the application
echo "Testing the application..."
curl -s http://localhost:8000/health

echo ""
echo "Application restarted without Sentry!"
echo ""
echo "To test the login endpoint, use the emergency login:"
echo "curl -X POST http://localhost:8000/api/v1/auth/emergency-login -H \"Content-Type: application/json\" -d '{\"email\":\"admin@example.com\",\"password\":\"password\"}'"