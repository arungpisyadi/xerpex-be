#!/bin/bash
# Script to restart the service after code changes

# Set error handling
set -e
echo "Starting service restart..."

# Check if running in Docker or directly on the server
if command -v docker &> /dev/null && docker ps | grep -q kebunsu-api; then
    echo "Docker environment detected. Restarting Docker container..."
    docker restart kebunsu-api
    echo "Docker container restarted."
else
    echo "Non-Docker environment detected. Checking for service management..."
    
    # Check if using supervisor
    if command -v supervisorctl &> /dev/null; then
        echo "Supervisor detected. Restarting service..."
        # Try to restart the service
        sudo supervisorctl restart xerpex || {
            echo "Error restarting service. Checking supervisor logs..."
            sudo tail -n 50 /var/log/supervisor/supervisord.log
            
            echo "Trying to update supervisor configuration..."
            sudo supervisorctl reread
            sudo supervisorctl update
            sudo supervisorctl restart xerpex
        }
    # Check if using systemd
    elif command -v systemctl &> /dev/null; then
        echo "Systemd detected. Restarting service..."
        sudo systemctl restart xerpex || {
            echo "Error restarting service. Checking systemd logs..."
            sudo journalctl -u xerpex -n 50
        }
    else
        echo "No service manager detected. Trying to restart manually..."
        
        # Try to find and kill any running uvicorn processes
        pkill -f "uvicorn app.main:app" || echo "No running uvicorn processes found."
        
        # Start the application in the background
        echo "Starting application manually..."
        cd /opt/xerpex
        source venv/bin/activate
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
        
        echo "Application started with PID: $!"
    fi
fi

# Wait for the service to start
echo "Waiting for service to start..."
sleep 5

# Test the connection
echo "Testing connection..."
curl -s http://localhost:8000/test-connection || echo "Could not connect to test endpoint."

echo "Service restart completed."