# Fixing Missing Package Errors

Based on your error logs, your Docker container is restarting because it's missing required Python packages. This guide will help you fix these issues.

## Identified Missing Packages

1. **pydantic_settings**:
   ```
   ModuleNotFoundError: No module named 'pydantic_settings'
   ```

2. **sentry_sdk**:
   ```
   ModuleNotFoundError: No module named 'sentry_sdk'
   ```

3. **mysqlclient** (provides MySQLdb):
   ```
   ModuleNotFoundError: No module named 'MySQLdb'
   ```

4. **email-validator**:
   ```
   ImportError: email-validator is not installed, run `pip install pydantic[email]`
   ```

5. **python-jose**:
   ```
   ModuleNotFoundError: No module named 'jose'
   ```

6. **python-multipart**:
   ```
   RuntimeError: Form data requires "python-multipart" to be installed.
   ```

## Quick Fix

1. Add the missing packages to your requirements.txt file
2. Rebuild your Docker image
3. Restart your containers

## Detailed Solution

### 1. Add the Missing Packages to requirements.txt

The errors occur because your application is trying to import packages that are not installed in the Docker container:
- `pydantic_settings` is imported in `app/config.py`
- `sentry_sdk` is imported in `app/main.py`
- `MySQLdb` is needed by SQLAlchemy to connect to MySQL in `app/database.py`
- `email-validator` is needed by Pydantic for email field validation in your schemas
- `python-jose` is imported as `jose` in `app/utils/security.py` for JWT token handling
- `python-multipart` is needed by FastAPI for handling form data in your API endpoints

Edit your requirements.txt file:

```bash
# SSH into your server and navigate to your project directory
cd /path/to/xerpex-be

# Edit the requirements.txt file
nano requirements.txt
```

Add the following lines to your requirements.txt file:

```
pydantic-settings==2.0.3
sentry-sdk==1.30.0
mysqlclient==2.2.0
email-validator==2.0.0
python-jose==3.3.0
python-multipart==0.0.6
```

Save the file and exit the editor.

### 2. Rebuild Your Docker Image

Now you need to rebuild your Docker image with the updated requirements:

```bash
# Stop the current containers
docker compose down

# Rebuild the image without using cache
docker compose build --no-cache

# Start the containers again
docker compose up -d
```

### 3. Verify the Fix

Check if the container is running properly now:

```bash
# Check container status
docker ps

# If it's still restarting, check the logs
docker logs kebunsu-api
```

## Alternative Solutions

If you can't modify the requirements.txt file or rebuild the image for some reason, you can try these alternatives:

### Option 1: Install the Package Directly in the Container

```bash
# Execute a command in the running container (even if it's restarting)
docker exec -it kebunsu-api pip install pydantic-settings==2.0.3

# Then restart the container
docker restart kebunsu-api
```

### Option 2: Create a Custom Dockerfile

If you need a more permanent solution without modifying the original files:

1. Create a new Dockerfile:

```bash
nano Dockerfile.custom
```

2. Add the following content:

```dockerfile
FROM xerpex-be-api:latest

# Install the missing packages
RUN pip install pydantic-settings==2.0.3 sentry-sdk==1.30.0 mysqlclient==2.2.0 email-validator==2.0.0 python-jose==3.3.0 python-multipart==0.0.6
```

3. Build and use this custom image:

```bash
docker build -t xerpex-be-api:fixed -f Dockerfile.custom .

# Update your docker-compose.yml to use this image
# Change the 'image' line to 'image: xerpex-be-api:fixed'
```

## Understanding the Issues

### pydantic_settings Issue

This error occurs because your application is using a newer version of Pydantic (v2.x) which has separated settings functionality into a separate package called `pydantic-settings`. In older versions of Pydantic (v1.x), the settings functionality was included in the main package.

In your `app/config.py` file, you're importing:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
```

But this package is not listed in your requirements.txt file, which only includes:

```
pydantic==2.3.0
pydantic_core==2.6.3
```

### sentry_sdk Issue

Your application uses Sentry for error tracking and monitoring. In your `app/main.py` file, you're importing:

```python
import sentry_sdk
```

But this package is not listed in your requirements.txt file.

### mysqlclient Issue

Your application uses SQLAlchemy with MySQL, which requires the `mysqlclient` package (which provides the `MySQLdb` module). In your `app/database.py` file, SQLAlchemy is trying to create an engine with the MySQL dialect:

```python
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
```

The URI is using the `mysql+mysqldb://` prefix, which requires the `mysqlclient` package, but it's not listed in your requirements.txt file.

### email-validator Issue

Your application uses Pydantic's email validation in your schema models. When you define a field with `EmailStr` type, Pydantic requires the `email-validator` package to validate email addresses:

```python
class UserLogin(BaseModel):
    email: EmailStr
    password: str
```

Without this package, you'll get the error:

```
ImportError: email-validator is not installed, run `pip install pydantic[email]`
```

### python-jose Issue

Your application uses JWT (JSON Web Tokens) for authentication, which requires the `python-jose` package. In your `app/utils/security.py` file, you're importing:

```python
from jose import jwt
```

This package is used for creating and verifying JWT tokens for user authentication, but it's not listed in your requirements.txt file.

### python-multipart Issue

Your application uses FastAPI's form data handling, which requires the `python-multipart` package. When you define an endpoint that accepts form data, FastAPI requires this package:

```python
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # ...
```

Without this package, you'll get the error:

```
RuntimeError: Form data requires "python-multipart" to be installed.
```

## Preventing Similar Issues in the Future

To prevent similar issues in the future:

1. **Use a package freeze tool**: Generate your requirements.txt using `pip freeze > requirements.txt` in your development environment to ensure all dependencies are captured.

2. **Use a dependency management tool**: Consider using tools like Poetry or Pipenv that better handle dependency resolution.

3. **Test your Docker build locally**: Before deploying, build and test your Docker image locally to catch any missing dependencies.

4. **Add a health check to your Docker Compose file**: This can help detect issues earlier:

```yaml
services:
  api:
    # ... other settings ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Next Steps

After fixing this issue:

1. Check for any other missing packages in your logs
2. Verify that your application can connect to the database
3. Continue with the Nginx configuration to fix the 502 Bad Gateway error

Remember to check the application logs if you encounter any other issues:

```bash
docker logs kebunsu-api
```

## Complete Updated requirements.txt

For your convenience, here's the complete updated requirements.txt file with all necessary packages:

```
alembic==1.12.0
annotated-types==0.5.0
anyio==3.7.1
bcrypt==4.3.0
click==8.1.7
colorama==0.4.6
email-validator==2.0.0
fastapi==0.103.1
h11==0.14.0
idna==3.4
mysql-connector-python==9.4.0
mysqlclient==2.2.0
passlib==1.7.4
pydantic==2.3.0
pydantic-settings==2.0.3
pydantic_core==2.6.3
python-dotenv==1.1.1
python-jose==3.3.0
python-memcached==1.59
python-multipart==0.0.6
sentry-sdk==1.30.0
six==1.16.0
sniffio==1.3.0
SQLAlchemy==2.0.20
starlette==0.27.0
typing_extensions==4.8.0
uvicorn==0.23.2
```

You can use this to replace your current requirements.txt file entirely.