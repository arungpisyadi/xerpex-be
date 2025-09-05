# XerpeX ERP System - Setup Guide

This guide provides detailed instructions for setting up and running the XerpeX ERP system.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker and Docker Compose** (for containerized setup)
- **Python 3.11+** (for local development)
- **MySQL** (for local development without Docker)
- **Git** (for version control)

## Installation Options

You can set up the XerpeX ERP system in two ways:

1. **Docker Setup** (Recommended for production and consistent development)
2. **Local Setup** (For development without Docker)

## Docker Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/erp-kebunsu-be.git
cd erp-kebunsu-be
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

Edit the `.env` file to set your environment variables:

```
# API settings
PROJECT_NAME=XerpeX ERP System
API_V1_STR=/api/v1

# Security settings
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8 days

# Database settings
# For remote database (e.g., AWS RDS, Azure Database, etc.)
MYSQL_SERVER=your-db-instance.region.rds.amazonaws.com
MYSQL_USER=your_db_username
MYSQL_PASSWORD=your_db_password
MYSQL_DB=kebunsu_erp
MYSQL_PORT=3306

# CORS settings
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

Make sure to replace the database connection details with your actual remote database credentials.

### 3. Build and Start the Containers

```bash
docker-compose up -d
```

This command will:
- Build the Docker image
- Create and start the container
- Connect to your remote database
- Apply migrations
- Start the FastAPI application

### 4. Verify the Setup

The API should now be running at http://localhost:8000

You can access:
- API documentation: http://localhost:8000/api/v1/docs
- Alternative API documentation: http://localhost:8000/api/v1/redoc

### 5. Stopping the Containers

To stop the containers:

```bash
docker-compose down
```

To stop the containers and remove volumes (this will delete all data):

```bash
docker-compose down -v
```

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/erp-kebunsu-be.git
cd erp-kebunsu-be
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:
  ```bash
  venv\Scripts\activate
  ```

- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

Edit the `.env` file to set your environment variables:

```
# API settings
PROJECT_NAME=XerpeX ERP System
API_V1_STR=/api/v1

# Security settings
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8 days

# Database settings
MYSQL_SERVER=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=kebunsu_erp
MYSQL_PORT=3306

# CORS settings
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

### 5. Set Up the Database

Create a MySQL database named `kebunsu_erp` (or use the name specified in your `.env` file):

```bash
mysql -u root -p -e "CREATE DATABASE kebunsu_erp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Apply migrations:

```bash
alembic upgrade head
```

### 6. Run the Application

```bash
uvicorn app.main:app --reload
```

The API should now be running at http://localhost:8000

## Database Migrations

### Creating a New Migration

After making changes to the database models, create a new migration:

```bash
alembic revision --autogenerate -m "description of changes"
```

### Applying Migrations

#### Local Environment

Apply all pending migrations:

```bash
alembic upgrade head
```

Apply migrations up to a specific version:

```bash
alembic upgrade <revision_id>
```

#### Docker Environment

Run migrations within the Docker container:

```bash
docker-compose exec app alembic upgrade head
```

### Migration Management

Check current migration status:

```bash
alembic current
```

View migration history:

```bash
alembic history --verbose
```

### Downgrading Migrations

Downgrade to a previous version:

```bash
alembic downgrade <revision_id>
```

Downgrade one version:

```bash
alembic downgrade -1
```

Downgrade all migrations (revert to empty database):

```bash
alembic downgrade base
```

## Initial Data Setup

The system includes a script to create initial data, including an admin user.

### Using Docker

```bash
docker-compose exec app python -m app.initial_data
```

### Local Setup

```bash
python -m app.initial_data
```

This will create:
- An admin user (email: admin@kebunsu.com, password: admin)
- Sample villas
- Test data for development

## Running Tests

### Using Docker

```bash
docker-compose exec app pytest
```

### Local Setup

```bash
pytest
```

For test coverage:

```bash
pytest --cov=app
```

## Database Setup Options

This application is configured to connect to an external database server instead of running a database in a Docker container. You have several options:

### Option 1: Connecting to a Cloud Database (AWS RDS, Azure, etc.)

1. Create a MySQL database instance on your preferred cloud provider (AWS RDS, Azure, GCP, etc.)
2. Configure the database with appropriate security settings:
   - Set up a secure password
   - Configure network access (security groups, firewall rules) to allow connections from your application
   - Consider using SSL/TLS for secure connections

### Option 2: Connecting to a Database on Windows Host from Docker Desktop

If you're running Docker Desktop on Windows and want to connect to a MySQL database running on your Windows host (localhost):

1. Install and set up MySQL on your Windows machine
2. Configure MySQL to accept connections:
   - Edit `my.cnf` to set `bind-address = '0.0.0.0'`
   - Ensure the MySQL user has permissions to connect from any host (`'%'`)
3. In your `.env` file, use the special DNS name `host.docker.internal` to refer to your Windows host:
   ```
   MYSQL_SERVER=host.docker.internal
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DB=kebunsu_erp
   MYSQL_PORT=3306
   ```
4. Make sure your Windows firewall allows connections to MySQL (port 3306)

### Configuring the Application

1. Update your `.env` file with the appropriate database connection details:

   **For cloud databases (AWS RDS, Azure, etc.):**
   ```
   MYSQL_SERVER=your-db-instance.region.rds.amazonaws.com
   MYSQL_USER=your_db_username
   MYSQL_PASSWORD=your_db_password
   MYSQL_DB=kebunsu_erp
   MYSQL_PORT=3306
   ```

   **For Windows users with Docker Desktop connecting to localhost:**
   ```
   MYSQL_SERVER=host.docker.internal
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DB=kebunsu_erp
   MYSQL_PORT=3306
   ```

2. Ensure your database is accessible from the environment where your application is running:
   - For local development: Your local machine needs network access to the database
   - For Docker: The Docker container is configured with `network_mode: "host"` to allow it to access external networks
   - For production: Your production server needs network access to the database

3. Important Docker Network Configuration:
   - The Docker Compose file provides multiple network configuration options:
     
     a) **Host Network Mode** (best for Linux):
     ```yaml
     network_mode: "host"
     ```
     
     b) **Bridge Network** (best for Windows/macOS with Docker Desktop):
     ```yaml
     networks:
       - kebunsu-network
     ```
     
     c) **Special Configuration for Windows localhost connections**:
     ```yaml
     extra_hosts:
       - "host.docker.internal:host-gateway"
     ```
     
   - Choose the appropriate option by uncommenting the relevant lines in the docker-compose.yml file
   - The host network mode provides better performance but has limitations on Windows and macOS
   - The bridge network works on all platforms but might require additional configuration for certain network scenarios
   - For Windows users connecting to a database on localhost, the `host.docker.internal` DNS name is used to refer to the host machine from inside the container, and the `extra_hosts` configuration ensures this DNS name resolves correctly

3. Apply migrations to set up the database schema:
   - Local: `alembic upgrade head`
   - Docker: `docker-compose exec api alembic upgrade head`

## Troubleshooting

### Database Connection Issues

1. Verify your remote database service is running and accessible
2. Check the database connection details in your .env file
3. Ensure the database exists on your remote server
4. Verify network connectivity:
   - Check if your IP is allowed in the database security group/firewall
   - Test connection using a tool like `mysql` command-line client or a database client
   - Check for any VPN or network restrictions

### Migration Errors

If you encounter migration errors:

1. Reset the migrations (for development only):
   ```bash
   alembic downgrade base
   ```
2. Remove any conflicting migration files
3. Create a new migration:
   ```bash
   alembic revision --autogenerate -m "fresh migration"
   ```
4. Apply the new migration:
   ```bash
   alembic upgrade head
   ```

### Docker Issues

If you encounter issues with Docker:

1. Check Docker logs:
   ```bash
   docker-compose logs
   ```
2. Rebuild the containers:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Production Deployment

For production deployment:

1. Use a proper secret key in the .env file
2. Set up SSL/TLS with a reverse proxy (Nginx or Traefik)
3. Configure database backups
4. Set up monitoring and logging
5. Consider using Docker Swarm or Kubernetes for orchestration

### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name api.kebunsu.com;
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name api.kebunsu.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security Considerations

1. **Environment Variables**: Never commit .env files to version control
2. **Secret Key**: Use a strong, randomly generated secret key
3. **Database Credentials**: Use strong passwords and consider using environment-specific credentials
4. **API Access**: Implement rate limiting for production
5. **Regular Updates**: Keep dependencies updated to patch security vulnerabilities

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [MySQL Documentation](https://dev.mysql.com/doc/)