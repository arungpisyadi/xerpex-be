#!/bin/bash
# Script to deploy fixes for the 504 timeout issue

# Set error handling
set -e
echo "Starting deployment of fixes for 504 timeout issue..."

# 1. Stop the current services
echo "Stopping current services..."
docker compose down

# 2. Apply Nginx configuration changes
echo "Applying Nginx configuration changes..."
sudo cp nginx-cors-fix.conf /etc/nginx/sites-available/kebunsu-be-staging
sudo nginx -t
sudo systemctl reload nginx

# 3. Rebuild and restart the Docker containers
echo "Rebuilding and restarting Docker containers..."
docker compose build --no-cache
docker compose up -d

# 4. Wait for services to start
echo "Waiting for services to start..."
sleep 10

# 5. Test the database connection
echo "Testing database connection..."
docker exec kebunsu-api python test_db_connection.py

# 6. Test the API health endpoints
echo "Testing API health endpoints..."
curl -s http://localhost:8000/health | grep -q "healthy" && echo "Basic health check: OK" || echo "Basic health check: FAILED"
curl -s http://localhost:8000/health/db | grep -q "database" && echo "Database health check: OK" || echo "Database health check: FAILED"

echo "Deployment completed. Please verify that the login functionality is working correctly."