# Fixing Docker Container Restart Issues

Based on your Docker container status:

```
7f241ea8ed5e   xerpex-be-api   "bash -c 'alembic up…"   4 minutes ago   Restarting (1) 55 seconds ago             kebunsu-api
```

Your container is continuously restarting while trying to run Alembic migrations. This guide will help you diagnose and fix the issue.

## Quick Diagnosis Steps

1. Check container logs
2. Verify database connection
3. Check environment variables
4. Inspect Alembic migration files
5. Test database connection manually

## Detailed Troubleshooting

### 1. Check Container Logs

The first step is to check the container logs to see the exact error:

```bash
# View the logs of the restarting container
docker logs kebunsu-api

# For more detailed logs with timestamps
docker logs --timestamps kebunsu-api

# To follow the logs in real-time
docker logs -f kebunsu-api
```

Look for error messages related to:
- Database connection failures
- Alembic migration errors
- Permission issues
- Import errors or other Python exceptions

### 2. Verify Database Connection

Since the container is failing during Alembic migrations, the most likely issue is a database connection problem:

```bash
# Check if MySQL is running (if it's on the same host)
sudo systemctl status mysql

# Check if you can connect to the database from the host
mysql -u root -p -h localhost
```

If you're using a remote database or a database in another container:

```bash
# Check if the database container is running
docker ps | grep mysql

# Try connecting to the database from another container
docker exec -it kebunsu-api bash -c "mysql -u root -p -h mysql_host"
```

### 3. Check Environment Variables

Verify that your environment variables are correctly set:

```bash
# Check the environment variables in the container
docker inspect kebunsu-api | grep -A 20 "Env"

# Or exec into the container and check
docker exec -it kebunsu-api env
```

Make sure these critical variables are correctly set:
- `MYSQL_SERVER`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB`
- `MYSQL_PORT`

### 4. Check Docker Compose Configuration

Review your docker-compose.yml file:

```bash
cat docker-compose.yml
```

Ensure the database connection details are correct and that the networks are properly configured.

### 5. Inspect Alembic Migration Files

If the issue is with specific migrations:

```bash
# List migration files
ls -la migrations/versions/

# Check the content of the latest migration file
cat migrations/versions/$(ls -t migrations/versions/ | head -1)
```

Look for any issues in the migration files that might be causing errors.

## Common Issues and Solutions

### Issue 1: Database Connection Failure

**Symptoms in logs:**
- "Can't connect to MySQL server"
- "Access denied for user"
- "Unknown database"

**Solutions:**

1. **Incorrect database host:**
   
   If you're using Docker's bridge network, containers can't use `localhost` to refer to the host machine. Update your `.env` file:

   ```
   # Change this
   MYSQL_SERVER=localhost
   
   # To this (for Docker Desktop on Windows/Mac)
   MYSQL_SERVER=host.docker.internal
   
   # Or to this (for Docker bridge network)
   MYSQL_SERVER=mysql  # The service name of your MySQL container
   ```

2. **Incorrect credentials:**
   
   Verify your database username and password in the `.env` file.

3. **Database doesn't exist:**
   
   Create the database manually:

   ```bash
   mysql -u root -p -e "CREATE DATABASE xerpex_erp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```

4. **Network issues:**
   
   If using separate containers, ensure they're on the same Docker network:

   ```yaml
   # In docker-compose.yml
   services:
     api:
       # ... other settings ...
       networks:
         - xerpex-network
     
     mysql:
       # ... other settings ...
       networks:
         - xerpex-network
   
   networks:
     xerpex-network:
       driver: bridge
   ```

### Issue 2: Alembic Migration Errors

**Symptoms in logs:**
- "Error creating tables"
- "Column already exists"
- "Syntax error in SQL statement"

**Solutions:**

1. **Reset migrations (for development only):**
   
   ```bash
   # Connect to the database
   mysql -u root -p xerpex_erp
   
   # Drop the alembic_version table
   DROP TABLE alembic_version;
   
   # Exit MySQL
   exit
   
   # Then restart your container
   docker restart kebunsu-api
   ```

2. **Fix specific migration issues:**
   
   If a specific migration is causing problems, you might need to modify it or create a new migration that fixes the issue.

### Issue 3: Permission Issues

**Symptoms in logs:**
- "Permission denied"
- "Could not open file"

**Solutions:**

1. **Fix file permissions:**
   
   ```bash
   # Change ownership of the project files
   sudo chown -R 1000:1000 /path/to/your/project
   ```

2. **Check volume mounts:**
   
   Ensure your Docker volume mounts have the correct permissions.

### Issue 4: Resource Constraints

**Symptoms:**
- Container exits without clear error messages
- "Killed" message in logs

**Solutions:**

1. **Check system resources:**
   
   ```bash
   # Check memory usage
   free -m
   
   # Check disk space
   df -h
   ```

2. **Increase container resources:**
   
   If you're using resource limits in Docker Compose, increase them:

   ```yaml
   services:
     api:
       # ... other settings ...
       deploy:
         resources:
           limits:
             cpus: '1'
             memory: 1G
   ```

## Specific Fix for Alembic Migration Issues

If the issue is specifically with Alembic migrations:

1. **Temporarily modify the command in docker-compose.yml:**

   ```yaml
   services:
     api:
       # ... other settings ...
       # Change this
       command: >
         bash -c "alembic upgrade head &&
                 uvicorn app.main:app --host 0.0.0.0 --port 8000"
       
       # To this (temporarily skip migrations)
       command: >
         bash -c "uvicorn app.main:app --host 0.0.0.0 --port 8000"
   ```

2. **Run migrations manually with more verbose output:**

   ```bash
   docker exec -it kebunsu-api bash
   cd /app
   alembic upgrade head --sql
   ```

   This will show the SQL that would be executed without actually running it.

3. **Check database connectivity from inside the container:**

   ```bash
   docker exec -it kebunsu-api bash
   python -c "from app.database import engine; print(engine.connect())"
   ```

## Testing the Fix

After making changes:

1. **Restart the container:**

   ```bash
   docker compose down
   docker compose up -d
   ```

2. **Monitor the logs:**

   ```bash
   docker logs -f kebunsu-api
   ```

3. **Check if the container stays running:**

   ```bash
   docker ps | grep kebunsu-api
   ```

## Advanced Debugging

For more advanced debugging:

1. **Run the container with an interactive shell instead of the normal command:**

   ```bash
   docker run -it --rm --entrypoint bash xerpex-be-api
   ```

   This will give you a shell inside the container without running the application.

2. **Test each component separately:**

   ```bash
   # Test database connection
   python -c "import mysql.connector; print(mysql.connector.connect(host='your_host', user='your_user', password='your_password', database='your_db'))"
   
   # Test Alembic
   alembic current
   
   # Test the application without migrations
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Conclusion

Container restart issues are usually caused by:

1. Database connection problems
2. Migration errors
3. Environment variable misconfiguration
4. Resource constraints

By checking the container logs and following the steps in this guide, you should be able to identify and fix the specific issue causing your container to restart.

Remember to check the logs first, as they will provide the most direct information about what's going wrong.