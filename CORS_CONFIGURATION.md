# Fixing CORS Issues in XerpeX ERP Deployment

## The Issue

You're encountering a CORS (Cross-Origin Resource Sharing) error:

```
Access to XMLHttpRequest at 'https://kebunsu-be-staging.tugugroup.co.id/api/v1/auth/login/json' 
from origin 'https://kebunsu-staging.tugugroup.co.id' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

This happens because:
1. Your frontend (https://kebunsu-staging.tugugroup.co.id) and backend (https://kebunsu-be-staging.tugugroup.co.id) are on different domains
2. The browser enforces the Same-Origin Policy, which prevents JavaScript from making requests to a different domain
3. CORS headers are not properly configured on your backend to allow requests from your frontend domain

## Solution

You need to configure CORS in two places:

1. In your FastAPI application
2. In your Nginx configuration

### 1. Check FastAPI CORS Configuration

Your FastAPI application already has CORS middleware configured in `app/main.py`:

```python
# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

But you need to ensure that your frontend domain is included in the `BACKEND_CORS_ORIGINS` setting.

### 2. Update Environment Variables

Edit your `.env` file to include your frontend domain in the `BACKEND_CORS_ORIGINS` setting:

```bash
# SSH into your server
cd /path/to/xerpex-be

# Edit the .env file
nano .env
```

Update the `BACKEND_CORS_ORIGINS` line:

```
# Change this:
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# To this (include your frontend domain):
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "https://kebunsu-staging.tugugroup.co.id"]
```

### 3. Add CORS Headers in Nginx

Even with the FastAPI CORS configuration, it's a good practice to also configure CORS in Nginx, especially for handling preflight requests.

Edit your Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/kebunsu-be-staging
```

Add CORS headers to your server block:

```nginx
server {
    listen 80;
    server_name kebunsu-be-staging.tugugroup.co.id;
    
    # Add these CORS headers
    add_header 'Access-Control-Allow-Origin' 'https://kebunsu.tugugroup.co.id' always;
    add_header 'Access-Control-Allow-Origin' 'https://kebunsu-staging.tugugroup.co.id' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE, PATCH' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
    
    location / {
        # Handle preflight requests (OPTIONS)
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' 'https://kebunsu-staging.tugugroup.co.id' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE, PATCH' always;
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Test and Apply Changes

1. Test the Nginx configuration:
   ```bash
   sudo nginx -t
   ```

2. Reload Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

3. Restart your FastAPI application:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Verifying the Fix

You can verify that CORS is properly configured by:

1. Checking the response headers in your browser's developer tools:
   - Make a request from your frontend to your backend
   - In the Network tab, check that the response includes the `Access-Control-Allow-Origin` header

2. Using curl to test the CORS headers:
   ```bash
   curl -X OPTIONS -H "Origin: https://kebunsu-staging.tugugroup.co.id" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type, Authorization" \
     -I https://kebunsu-be-staging.tugugroup.co.id/api/v1/auth/login/json
   ```

   You should see the CORS headers in the response.

## Troubleshooting

If you're still experiencing CORS issues:

1. **Check the actual values in your environment**:
   ```bash
   docker compose exec api env | grep CORS
   ```

2. **Verify the FastAPI middleware is being applied**:
   - Add some debug logging in your FastAPI application
   - Check the logs to ensure the CORS middleware is being initialized with the correct origins

3. **Test with a wildcard origin temporarily**:
   - In your `.env` file: `BACKEND_CORS_ORIGINS=["*"]`
   - In Nginx: `add_header 'Access-Control-Allow-Origin' '*' always;`
   - Note: This is not recommended for production, but useful for testing

4. **Check for any other proxies or CDNs**:
   - If you're using a CDN or another proxy, ensure it's not stripping the CORS headers

## Security Considerations

When configuring CORS:

1. **Be specific with origins**: Only allow the specific domains that need access, not wildcard `*`
2. **Limit methods and headers**: Only allow the methods and headers your application needs
3. **Consider credentials**: If using `allow_credentials=True`, you cannot use wildcard origins
4. **Use HTTPS**: Always use HTTPS for both frontend and backend in production

By properly configuring CORS, you'll allow your frontend application to communicate with your backend API while maintaining security.