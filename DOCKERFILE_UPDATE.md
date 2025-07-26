# Updating the Dockerfile for MySQL Support

When deploying your XerpeX ERP backend, you may encounter issues with the `mysqlclient` Python package, which requires specific system libraries to be installed in the Docker container.

## The Issue

The error message you might see in your Docker logs:

```
ModuleNotFoundError: No module named 'MySQLdb'
```

This occurs because:

1. Your application uses SQLAlchemy with the MySQL dialect, which requires the `mysqlclient` Python package
2. The `mysqlclient` package needs system-level MySQL development libraries to compile and install
3. These libraries are not included in the base Docker image

## The Solution

You need to update your Dockerfile to install the required system dependencies before installing the Python packages.

### 1. Update the Dockerfile

Edit your Dockerfile:

```bash
nano Dockerfile
```

Find the section where system dependencies are installed (around line 11-14):

```dockerfile
# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

Update it to include MySQL development libraries:

```dockerfile
# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev default-libmysqlclient-dev pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
```

The key additions are:
- `default-libmysqlclient-dev`: MySQL client development files
- `pkg-config`: Helper tool used during compilation
- `pip install --upgrade pip`: Ensures the latest pip version is used
- Order of operations: System dependencies must be installed before Python packages

### 2. Update requirements.txt

Ensure your requirements.txt includes the mysqlclient package:

```
mysqlclient==2.2.0
```

### 3. Rebuild the Docker Image

After making these changes, rebuild your Docker image:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Why This Works

The `mysqlclient` Python package is a compiled extension that interfaces with the MySQL C client library. When you install it with pip, it needs to compile C code against the MySQL development headers.

By adding `default-libmysqlclient-dev` to your Dockerfile, you're providing these necessary development headers and libraries so that the compilation process can succeed.

## Alternative Approaches

If you prefer not to modify the Dockerfile, you could:

1. **Use a different MySQL dialect**: SQLAlchemy supports other MySQL dialects like `pymysql` which is pure Python and doesn't require C extensions:
   ```python
   # In database.py, change:
   # mysql+mysqldb:// to mysql+pymysql://
   ```

2. **Use a pre-built Docker image**: There are Docker images available that already include MySQL client libraries.

However, updating the Dockerfile as described above is the most straightforward approach and ensures that your application has all the dependencies it needs.

## Verifying the Fix

After rebuilding your Docker image, check the logs to ensure there are no more errors:

```bash
docker logs kebunsu-api
```

You should see your application starting up without the `ModuleNotFoundError: No module named 'MySQLdb'` error.

## Common Build Errors

If you encounter this error during the Docker build:

```
/bin/sh: 1: pkg-config: not found
Command 'pkg-config --exists mysqlclient' returned non-zero exit status 127.
```

It means that the `pkg-config` tool is not available during the build process. This can happen if:

1. The system dependencies are not installed before the Python dependencies
2. The `pkg-config` package is not included in the list of system dependencies

Make sure your Dockerfile has the correct order of operations:
1. Install system dependencies first
2. Then copy the requirements.txt file
3. Then install Python dependencies

This ensures that all necessary system tools are available when the Python packages are being installed.