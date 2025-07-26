# Resolving "Address Already in Use" Port Conflict

When you see the error message:

```
INFO:     Will watch for changes in these directories: ['/app']
ERROR:    [Errno 98] Address already in use
```

This indicates that the port your application is trying to use (typically port 8000) is already being used by another process. Here's how to resolve this issue:

## Identifying the Process Using the Port

First, identify which process is using the port:

### On Linux/macOS:
```bash
sudo lsof -i :8000
```

### On Windows:
```bash
netstat -ano | findstr :8000
```

This will show you the process ID (PID) that's currently using port 8000.

## Resolving the Conflict

You have several options to resolve this port conflict:

### Option 1: Stop the Existing Process

If you don't need the process that's currently using port 8000:

#### On Linux/macOS:
```bash
# Replace 1234 with the actual PID from the lsof command
sudo kill -9 1234
```

#### On Windows:
```bash
# Replace 1234 with the actual PID from the netstat command
taskkill /F /PID 1234
```

### Option 2: Change the Port for Your Application

Modify your application to use a different port:

#### In docker-compose.yml:
```yaml
services:
  api:
    # ... other settings ...
    ports:
      - "8001:8000"  # Map container port 8000 to host port 8001
```

#### Or when running uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Option 3: Use the --reload-port Option

If you're using uvicorn with the --reload flag, you can specify a different port for the reloader:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-port 8100
```

## For Docker Environments

If you're running in Docker and experiencing this issue:

1. **Check if another container is using the port:**
   ```bash
   docker ps
   ```

2. **Stop conflicting containers:**
   ```bash
   docker stop container_name
   ```

3. **Modify your docker-compose.yml to use a different host port:**
   ```yaml
   services:
     api:
       # ... other settings ...
       ports:
         - "8001:8000"  # Map container port 8000 to host port 8001
   ```

4. **Restart your containers:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## For Production Environments

In production environments, you might want to:

1. **Use a process manager** like Supervisor or systemd to ensure only one instance runs
2. **Set up a reverse proxy** (Nginx, Apache) to handle port management
3. **Implement health checks** to detect and resolve port conflicts automatically

## Preventing Future Conflicts

To prevent future port conflicts:

1. **Document the ports** used by different services in your project
2. **Use environment variables** for port configuration to make it easily changeable
3. **Implement graceful shutdown** in your application to properly release ports
4. **Consider using service discovery** for more complex deployments

By following these steps, you should be able to resolve the "Address already in use" error and prevent it from occurring in the future.