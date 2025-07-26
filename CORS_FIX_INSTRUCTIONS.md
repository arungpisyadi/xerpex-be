# CORS Fix Instructions

This document provides instructions for fixing the CORS issue with the XerpeX ERP System.

## The Issue

The error message indicates that the 'Access-Control-Allow-Origin' header contains duplicate values:

```
Access to XMLHttpRequest at 'https://kebunsu-be-staging.tugugroup.co.id/api/v1/auth/login/json' 
from origin 'https://kebunsu-staging.tugugroup.co.id' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check: 
The 'Access-Control-Allow-Origin' header contains multiple values 'https://kebunsu-staging.tugugroup.co.id, https://kebunsu-staging.tugugroup.co.id', but only one is allowed.
```

This happens because the Nginx configuration has multiple `add_header` directives for 'Access-Control-Allow-Origin', which causes duplicate headers.

## Fix 1: Update FastAPI CORS Configuration

1. We've updated the `.env.staging` file to include the frontend domain in the `BACKEND_CORS_ORIGINS` setting:

```
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "https://kebunsu-staging.tugugroup.co.id"]
```

2. Apply this change to your staging environment:

```bash
# SSH into your server
ssh user@your-server-ip

# Navigate to your project directory
cd /path/to/xerpex-be

# Update the .env file with the new BACKEND_CORS_ORIGINS setting
nano .env
```

## Fix 2: Update Nginx Configuration

The main issue is in the Nginx configuration where multiple `add_header` directives for 'Access-Control-Allow-Origin' are causing duplicate headers.

1. Replace your current Nginx configuration with the one provided in `nginx-cors-fix.conf`:

```bash
# SSH into your server
ssh user@your-server-ip

# Backup the current configuration
sudo cp /etc/nginx/sites-available/kebunsu-be-staging /etc/nginx/sites-available/kebunsu-be-staging.bak

# Create a new configuration file
sudo nano /etc/nginx/sites-available/kebunsu-be-staging
```

2. Copy and paste the content from `nginx-cors-fix.conf` into this file.

3. Test and reload Nginx:

```bash
# Test the configuration
sudo nginx -t

# If the test is successful, reload Nginx
sudo systemctl reload nginx
```

## Fix 3: Restart the FastAPI Application

After updating the environment variables, you need to restart the FastAPI application:

```bash
# SSH into your server
ssh user@your-server-ip

# Navigate to your project directory
cd /path/to/xerpex-be

# Restart the Docker containers
docker compose down
docker compose up -d
```

## Testing the Fix

You can verify that CORS is properly configured by:

1. Using curl to test the CORS headers:

```bash
curl -X OPTIONS -H "Origin: https://kebunsu-staging.tugugroup.co.id" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization" \
  -I https://kebunsu-be-staging.tugugroup.co.id/api/v1/auth/login/json
```

You should see a single 'Access-Control-Allow-Origin' header in the response.

2. Testing the actual login from the frontend:
   - Open the frontend application at https://kebunsu-staging.tugugroup.co.id
   - Try to log in
   - Check the browser's developer tools to ensure there are no CORS errors

## Troubleshooting

If you're still experiencing CORS issues:

1. Check the response headers in your browser's developer tools:
   - Make a request from your frontend to your backend
   - In the Network tab, check that the response includes a single 'Access-Control-Allow-Origin' header

2. Verify the FastAPI middleware is being applied:
   - Check the logs to ensure the CORS middleware is being initialized with the correct origins:
   ```bash
   docker compose logs api | grep CORS
   ```

3. Check if the Nginx configuration is correct:
   ```bash
   sudo nginx -T | grep -A 20 "server_name kebunsu-be-staging"
   ```

4. If all else fails, you can temporarily use a wildcard origin for testing:
   - In your `.env` file: `BACKEND_CORS_ORIGINS=["*"]`
   - In Nginx: `add_header 'Access-Control-Allow-Origin' '*' always;`
   - Note: This is not recommended for production, but useful for testing