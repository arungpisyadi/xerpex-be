#!/bin/bash
# Script to diagnose and fix persistent timeout issues

# Set error handling
set -e
echo "Starting timeout diagnosis..."

# Check Nginx configuration
echo "Checking Nginx configuration..."
if command -v nginx &> /dev/null; then
    sudo nginx -t
    echo "Checking Nginx error logs..."
    sudo tail -n 50 /var/log/nginx/error.log
else
    echo "Nginx not found. Skipping Nginx checks."
fi

# Check database connectivity
echo "Testing database connectivity..."
curl -s http://localhost:8000/health/db
echo ""

# Check database tables
echo "Testing database tables..."
curl -s http://localhost:8000/test-db-tables
echo ""

# Check basic connectivity
echo "Testing basic connectivity..."
curl -s http://localhost:8000/test-connection
echo ""

# Check MySQL process list
echo "Checking MySQL process list..."
if command -v mysql &> /dev/null; then
    # Try to connect using environment variables if available
    if [ -f .env ]; then
        source .env
        mysql -u$MYSQL_USER -p$MYSQL_PASSWORD -h$MYSQL_SERVER -e "SHOW PROCESSLIST;"
    else
        echo "No .env file found. Please enter MySQL credentials manually:"
        read -p "MySQL User: " mysql_user
        read -sp "MySQL Password: " mysql_password
        echo ""
        read -p "MySQL Host: " mysql_host
        mysql -u$mysql_user -p$mysql_password -h$mysql_host -e "SHOW PROCESSLIST;"
    fi
else
    echo "MySQL client not found. Skipping MySQL process list check."
fi

# Check for slow queries
echo "Checking for slow queries..."
if command -v mysql &> /dev/null; then
    if [ -f .env ]; then
        source .env
        mysql -u$MYSQL_USER -p$MYSQL_PASSWORD -h$MYSQL_SERVER -e "SHOW VARIABLES LIKE 'slow_query%';"
        mysql -u$MYSQL_USER -p$MYSQL_PASSWORD -h$MYSQL_SERVER -e "SHOW VARIABLES LIKE 'long_query_time';"
    fi
fi

# Check system resources
echo "Checking system resources..."
echo "CPU usage:"
top -bn1 | head -n 20
echo "Memory usage:"
free -m
echo "Disk usage:"
df -h

# Apply fixes
echo "Would you like to apply fixes for the timeout issue? (y/n)"
read apply_fixes

if [ "$apply_fixes" == "y" ]; then
    echo "Applying fixes..."
    
    # Restart the application
    echo "Restarting the application..."
    ./restart_service.sh
    
    # Test the login endpoint with a simple request
    echo "Testing login endpoint with a simple request..."
    curl -X POST http://localhost:8000/api/v1/auth/login/json \
      -H "Content-Type: application/json" \
      -d '{"email":"test@example.com","password":"password"}'
    echo ""
    
    echo "Fixes applied. Please check if the timeout issue is resolved."
else
    echo "No fixes applied."
fi

echo "Diagnosis completed."