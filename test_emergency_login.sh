#!/bin/bash
# Script to restart the application and test the emergency login endpoint

# Set error handling
set -e
echo "Starting emergency login test..."

# Restart the application
echo "Restarting the application..."
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl restart xerpex || echo "Failed to restart with supervisor."
fi

if command -v systemctl &> /dev/null; then
    sudo systemctl restart xerpex || echo "Failed to restart with systemd."
fi

# Wait for the application to start
echo "Waiting for the application to start..."
sleep 10

# Test the emergency login endpoint
echo "Testing emergency login endpoint..."
curl -X POST http://localhost:8000/api/v1/auth/emergency-login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}'

echo ""
echo "If you received a token, the emergency login endpoint is working."
echo "You can now use this endpoint to bypass the database authentication."
echo ""
echo "To use the emergency login endpoint from the frontend:"
echo "1. Open the browser developer console (F12)"
echo "2. Run the following JavaScript code:"
echo ""
echo "fetch('https://kebunsu-api.tugugroup.co.id/api/v1/auth/emergency-login', {"
echo "  method: 'POST',"
echo "  headers: { 'Content-Type': 'application/json' },"
echo "  body: JSON.stringify({ email: 'admin@example.com', password: 'password' })"
echo "}).then(r => r.json()).then(data => {"
echo "  localStorage.setItem('token', data.access_token);"
echo "  console.log('Token saved to localStorage. You can now refresh the page and should be logged in.');"
echo "});"
echo ""
echo "This will save the token to localStorage, which should allow you to access the application."
echo "Note: This is a temporary solution until the database issues are resolved."