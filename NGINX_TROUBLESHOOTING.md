# Nginx Troubleshooting Guide for XerpeX ERP Deployment

This guide focuses specifically on troubleshooting Nginx-related issues in your XerpeX ERP deployment, particularly the 502 Bad Gateway error.

## Understanding the 502 Bad Gateway Error

A 502 Bad Gateway error occurs when Nginx (acting as a reverse proxy) cannot communicate with the upstream server (your FastAPI application). This can happen for several reasons:

1. The FastAPI application is not running
2. The FastAPI application is running but not accessible to Nginx
3. The Nginx configuration is incorrect
4. Network issues between Nginx and the FastAPI application

## Step-by-Step Troubleshooting Workflow

Follow this systematic approach to diagnose and fix the issue:

### Step 1: Verify Nginx is Running

```bash
# Check Nginx status
sudo systemctl status nginx

# If not running, start it
sudo systemctl start nginx
```

### Step 2: Check Nginx Configuration

```bash
# Test Nginx configuration syntax
sudo nginx -t

# View Nginx configuration
sudo cat /etc/nginx/sites-available/xerpex
```

Ensure your configuration looks similar to this:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or your server IP
    
    location / {
        proxy_pass http://localhost:8000;  # This should match your FastAPI port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 3: Check Nginx Error Logs

```bash
# View Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

Look for specific error messages like:
- `connect() failed (111: Connection refused)` - The FastAPI app is not running or not accessible
- `no live upstreams while connecting to upstream` - Similar issue, no backend server available
- `upstream timed out` - The FastAPI app is taking too long to respond

### Step 4: Verify Docker Containers are Running

```bash
# List running containers
docker ps

# If the API container is not running, check its logs
docker logs kebunsu-api
```

### Step 5: Check Docker Network Configuration

The way Docker networking is set up affects how Nginx can access your application:

```bash
# Check Docker networks
docker network ls

# Inspect the network your containers are using
docker network inspect kebunsu-network
```

### Step 6: Test the FastAPI Application Directly

Bypass Nginx and test if the FastAPI application is working:

```bash
# Test from the host machine
curl http://localhost:8000/health

# If that doesn't work, test from inside the container
docker exec -it kebunsu-api curl http://localhost:8000/health
```

## Common Issues and Solutions

### Issue 1: Nginx Cannot Connect to the FastAPI Application

If you see `connect() failed (111: Connection refused)` in Nginx error logs:

#### Solution A: Docker Bridge Network

If you're using Docker's bridge network, Nginx needs to connect to the container's IP, not localhost:

1. Find the container's IP:
   ```bash
   docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kebunsu-api
   ```

2. Update Nginx configuration:
   ```nginx
   location / {
       proxy_pass http://172.17.0.2:8000;  # Replace with your container's IP
       # other proxy settings...
   }
   ```

3. Reload Nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

#### Solution B: Use Host Network Mode

Alternatively, configure Docker to use the host network:

1. Edit docker-compose.yml:
   ```yaml
   services:
     api:
       # ... other settings ...
       network_mode: "host"
       # Remove or comment out the 'ports' section if using host mode
   ```

2. Restart the containers:
   ```bash
   docker compose down
   docker compose up -d
   ```

3. Keep Nginx configured to use localhost:8000

### Issue 2: FastAPI Application Not Starting Properly

If the Docker container is not running or restarting repeatedly:

1. Check the application logs:
   ```bash
   docker logs kebunsu-api
   ```

2. Common application issues:
   - Database connection problems
   - Missing environment variables
   - Permission issues
   - Port conflicts

3. Fix environment variables:
   ```bash
   # Check current environment variables
   docker compose config
   
   # Edit .env file if needed
   nano .env
   ```

4. Rebuild and restart:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

### Issue 3: Incorrect Nginx Configuration

If Nginx configuration has syntax errors or incorrect settings:

1. Create a minimal working configuration:
   ```bash
   sudo nano /etc/nginx/sites-available/xerpex
   ```

   Use this simple configuration:
   ```nginx
   server {
       listen 80;
       server_name _;
       
       location / {
           proxy_pass http://localhost:8000;
       }
   }
   ```

2. Test and reload:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. Gradually add back more complex configuration once basic connectivity works.

## Advanced Troubleshooting

### Debugging with tcpdump

If you need to see the actual network traffic:

```bash
# Install tcpdump
sudo apt install -y tcpdump

# Monitor traffic on port 8000
sudo tcpdump -i any port 8000 -nn
```

### Testing with a Simple Web Server

To verify if Nginx reverse proxy works at all, test with a simple web server:

```bash
# Install Python if not already installed
sudo apt install -y python3

# Run a simple HTTP server on port 8000
cd /tmp
echo "Hello World" > index.html
python3 -m http.server 8000
```

Then try accessing your site. If this works but your FastAPI app doesn't, the issue is with your application, not Nginx.

## XerpeX ERP Specific Configuration

For the XerpeX ERP backend specifically, ensure:

1. The database connection is properly configured in the `.env` file
2. The application is binding to `0.0.0.0` (all interfaces), not just `127.0.0.1`
3. The correct ports are exposed in the Docker configuration

## Quick Fixes to Try

If you're still stuck, try these quick fixes:

1. **Restart everything**:
   ```bash
   sudo systemctl restart nginx
   docker compose down
   docker compose up -d
   ```

2. **Rebuild the Docker image**:
   ```bash
   docker compose down
   docker rmi kebunsu-api:latest
   docker compose build --no-cache
   docker compose up -d
   ```

3. **Simplify your setup temporarily**:
   - Use host networking in Docker
   - Use a minimal Nginx configuration
   - Disable any firewalls temporarily for testing

4. **Check system resources**:
   ```bash
   # Check disk space
   df -h
   
   # Check memory usage
   free -m
   
   # Check CPU usage
   top
   ```

## Conclusion

Most 502 Bad Gateway errors in this setup are caused by:

1. Network configuration mismatches between Docker and Nginx
2. The FastAPI application not running or crashing
3. Database connection issues

By systematically working through this guide, you should be able to identify and fix the specific cause of your 502 error.