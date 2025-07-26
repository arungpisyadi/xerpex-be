# Fixing IPv6 Connection Issues in Nginx

Based on your error log:

```
2025/07/26 06:33:49 [error] 31413#31413: *112 connect() failed (111: Unknown error) while connecting to upstream, client: 104.197.69.115, server: kebunsu-be-staging.tugugroup.co.id, request: "GET / HTTP/1.1", upstream: "http://[::1]:8000/", host: "kebunsu-be-staging.tugugroup.co.id"
```

The specific issue is that Nginx is trying to connect to your FastAPI application using IPv6 localhost (`[::1]:8000`), but the application is either not listening on IPv6 or not accessible via that address.

## Quick Fix

1. Edit your Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/kebunsu-be-staging
```

2. Find the `proxy_pass` directive and change it from IPv6 to IPv4:

```nginx
# Change this:
proxy_pass http://[::1]:8000/;

# To this:
proxy_pass http://127.0.0.1:8000/;
```

3. Test and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Detailed Solution

### 1. Check Your Current Nginx Configuration

First, let's examine your current Nginx configuration:

```bash
sudo cat /etc/nginx/sites-available/kebunsu-be-staging
```

Look for the server block that contains the configuration for `kebunsu-be-staging.tugugroup.co.id`.

### 2. Modify the Nginx Configuration

Edit the configuration file:

```bash
sudo nano /etc/nginx/sites-available/kebunsu-be-staging
```

Make the following changes:

```nginx
server {
    listen 80;
    server_name kebunsu-be-staging.tugugroup.co.id;
    
    location / {
        # Change this line
        proxy_pass http://127.0.0.1:8000;
        
        # Keep these settings
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Verify Docker Container Networking

Since you're using Docker, make sure your container is properly exposing the port to the host:

1. Check if your container is running:

```bash
docker ps | grep kebunsu
```

2. Verify the port mapping:

```bash
docker port kebunsu-api
```

You should see something like `8000/tcp -> 0.0.0.0:8000` or `8000/tcp -> 127.0.0.1:8000`.

### 4. Check Docker Compose Configuration

If you're using Docker Compose, check your `docker-compose.yml` file:

```bash
cat docker-compose.yml
```

Ensure the ports are properly mapped:

```yaml
services:
  api:
    # ... other settings ...
    ports:
      - "8000:8000"  # This maps host port 8000 to container port 8000
```

Alternatively, if you're using host network mode:

```yaml
services:
  api:
    # ... other settings ...
    network_mode: "host"
    # No need for ports mapping with host network mode
```

### 5. Test Direct Connection to the API

Before reloading Nginx, test if you can connect directly to the API:

```bash
curl http://127.0.0.1:8000/health
```

If this doesn't work, the issue is with your FastAPI application, not Nginx.

### 6. Reload Nginx and Test

After making the changes:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Then try accessing your site again.

## Alternative Solutions

### Option 1: Explicitly Disable IPv6 in Nginx

If you want to ensure Nginx doesn't try to use IPv6:

```nginx
server {
    listen 80;
    # Remove any 'listen [::]:80' lines if present
    server_name kebunsu-be-staging.tugugroup.co.id;
    
    # ... rest of your configuration ...
}
```

### Option 2: Use Docker Container IP Instead of Localhost

If your FastAPI app is running in a Docker container with bridge networking:

1. Find the container's IP:

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kebunsu-api
```

2. Update Nginx to use that IP:

```nginx
location / {
    proxy_pass http://172.17.0.2:8000;  # Replace with your container's actual IP
    # ... rest of your proxy settings ...
}
```

### Option 3: Use Unix Socket for Communication

For better performance, you can configure your FastAPI app and Nginx to communicate via Unix socket:

1. Update your Docker Compose file to mount a socket volume:

```yaml
services:
  api:
    # ... other settings ...
    volumes:
      - ./:/app
      - /var/run/fastapi:/var/run/fastapi
```

2. Update your FastAPI app to listen on the Unix socket (requires code changes).

3. Update Nginx to use the Unix socket:

```nginx
location / {
    proxy_pass http://unix:/var/run/fastapi/app.sock;
    # ... rest of your proxy settings ...
}
```

## Debugging IPv6 Issues

If you want to understand why IPv6 is failing:

1. Check if IPv6 is enabled on your system:

```bash
cat /proc/sys/net/ipv6/conf/all/disable_ipv6
```

If this returns `1`, IPv6 is disabled.

2. Check if your FastAPI app is listening on IPv6:

```bash
netstat -tulpn | grep 8000
```

You should see entries for both IPv4 and IPv6 if the app is listening on both.

## Conclusion

The most straightforward fix is to change the `proxy_pass` directive in your Nginx configuration from `http://[::1]:8000/` to `http://127.0.0.1:8000/`. This tells Nginx to use IPv4 instead of IPv6 to connect to your FastAPI application.

If you continue to have issues after making this change, please check if your FastAPI application is actually running and listening on port 8000.