# Troubleshooting 502 Bad Gateway Error

If you're seeing a 502 Bad Gateway error when accessing your deployed XerpeX ERP backend, follow these troubleshooting steps to identify and resolve the issue.

## Quick Diagnosis Steps

1. Check if the FastAPI application is running
2. Verify Nginx configuration
3. Check Docker container status
4. Review application logs
5. Test direct access to the application
6. Check firewall settings

## Detailed Troubleshooting

### 1. Check if the FastAPI Application is Running

```bash
# Check if the Docker containers are running
docker ps

# Check the logs of the API container
docker logs kebunsu-api
```

Look for any error messages in the logs that might indicate why the application isn't starting properly.

### 2. Verify Nginx Configuration

```bash
# Check Nginx configuration syntax
sudo nginx -t

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

Common Nginx configuration issues:
- Incorrect proxy_pass URL
- Wrong port number
- Syntax errors in the configuration file

### 3. Check Docker Container Status and Network

```bash
# Check if the containers are running and their network settings
docker ps
docker network ls
docker network inspect kebunsu-network
```

Make sure the API container is running and properly connected to the network.

### 4. Test Direct Access to the Application

Try accessing the FastAPI application directly (bypassing Nginx):

```bash
# Install curl if not already installed
sudo apt install -y curl

# Test direct access to the FastAPI application
curl http://localhost:8000/health
```

If this works, the issue is with Nginx. If not, the issue is with the FastAPI application.

### 5. Common Issues and Solutions

#### Issue 1: FastAPI Application Not Running

**Symptoms:**
- Docker container is not running or restarting repeatedly
- Error messages in the application logs

**Solutions:**
- Check the application logs: `docker logs kebunsu-api`
- Verify environment variables: `docker compose config`
- Check if the database is accessible
- Ensure the `.env` file has the correct configuration

#### Issue 2: Nginx Configuration Problems

**Symptoms:**
- Nginx test shows errors
- Error logs indicate proxy issues

**Solutions:**

1. Update your Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/xerpex
```

Ensure it looks like this:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or server IP
    
    location / {
        proxy_pass http://localhost:8000;  # Make sure this matches your FastAPI port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

2. Test and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Issue 3: Docker Network Issues

**Symptoms:**
- Application is running but not accessible
- Nginx can't connect to the application

**Solutions:**

1. Update the `docker-compose.yml` file to use the correct network configuration:

```yaml
services:
  api:
    # ... other settings ...
    network_mode: "host"  # For Linux hosts
    # OR
    networks:
      - kebunsu-network
    ports:
      - "8000:8000"
```

2. Restart the containers:

```bash
docker compose down
docker compose up -d
```

#### Issue 4: Firewall Blocking Access

**Symptoms:**
- Application and Nginx are running but not accessible

**Solution:**
```bash
# Check UFW status
sudo ufw status

# Ensure necessary ports are open
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # If you need direct access to the API
```

## Specific Fix for Common 502 Bad Gateway Issue

The most common cause of a 502 Bad Gateway error in this setup is a mismatch between how Docker is networking and how Nginx is trying to access the application. Here's a specific fix:

1. **Update your Nginx configuration**:

```bash
sudo nano /etc/nginx/sites-available/xerpex
```

Change the `proxy_pass` line to use the Docker container's IP instead of localhost:

```nginx
# Find the Docker container's IP
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kebunsu-api

# Then update the proxy_pass line in Nginx config
proxy_pass http://172.17.0.2:8000;  # Replace with your container's actual IP
```

2. **Or update docker-compose.yml to use host network mode**:

```yaml
services:
  api:
    # ... other settings ...
    network_mode: "host"
    # Comment out or remove the 'networks' and 'ports' sections if using host mode
```

3. **Restart everything**:

```bash
# Restart Docker containers
docker compose down
docker compose up -d

# Restart Nginx
sudo systemctl restart nginx
```

## Advanced Debugging

If the above steps don't resolve the issue, try these advanced debugging techniques:

1. **Check if the application is binding to the correct address**:

```bash
# Check which addresses the application is listening on
sudo netstat -tulpn | grep 8000
```

The FastAPI application should be binding to `0.0.0.0:8000` to be accessible from outside the container.

2. **Test with a simple Nginx configuration**:

Create a minimal Nginx configuration to rule out complex configuration issues:

```nginx
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

3. **Check Docker logs in real-time**:

```bash
docker logs -f kebunsu-api
```

Watch the logs while making a request to see any errors in real-time.

## Still Having Issues?

If you're still experiencing problems after trying these solutions:

1. Check if the MySQL database is properly configured and accessible
2. Verify that all required environment variables are set correctly
3. Try rebuilding the Docker image from scratch
4. Check for any application-specific errors in the logs

Remember that the most common causes of 502 errors in this setup are:
1. The FastAPI application not running or crashing
2. Nginx unable to connect to the FastAPI application due to network configuration
3. Incorrect proxy_pass URL in the Nginx configuration

## Need More Help?

If you're still stuck after trying these solutions, please provide:
1. The output of `docker ps`
2. The Nginx error logs
3. The application logs from the Docker container
4. Your Nginx configuration file (with sensitive information redacted)

This additional information will help diagnose the specific issue you're facing.