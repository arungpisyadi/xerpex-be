# XerpeX ERP System

A comprehensive ERP system for managing villa bookings, payments, and reporting for XerpeX.

## Features

- **User Management**: Create, update, and manage user accounts with role-based access control
- **Villa Management**: Manage villa properties, availability, and pricing
- **Booking Management**: Create and manage bookings with villa assignments, packages, and add-ons
- **Payment Management**: Process payments, generate invoices, and track financial transactions
- **Reporting**: Generate comprehensive reports on occupancy, revenue, and booking status
- **Authentication**: Secure JWT-based authentication system
- **API Documentation**: Interactive API documentation with Swagger UI

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: MySQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest

## Project Structure

The project follows the MVC (Model-View-Controller) design pattern:

- **Models**: Database models representing the data structure
- **Schemas**: Pydantic schemas for request/response validation
- **Controllers**: API route controllers handling HTTP requests
- **Services**: Business logic services
- **Utils**: Utility functions and helpers

```
app/
├── controllers/     # API route controllers
├── models/          # Database models
├── schemas/         # Pydantic schemas
├── services/        # Business logic services
├── tests/           # Unit tests
├── utils/           # Utility functions
├── __init__.py
├── config.py        # Application configuration
├── database.py      # Database connection setup
└── main.py          # Main application entry point
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Environment Variables

Create a `.env` file in the root directory with the following variables (or use the provided `.env.example`):

```
# Database settings
MYSQL_SERVER=host.docker.internal
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DB=kebunsu_erp
MYSQL_PORT=3306

# Security settings
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8 days
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### Running with Docker

1. Build and start the containers:

```bash
docker-compose up -d
```

2. The API will be available at http://localhost:8000

3. Access the API documentation at http://localhost:8000/api/v1/docs

### Running Locally

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up the database:

```bash
alembic upgrade head
```

4. Run the application:

```bash
uvicorn app.main:app --reload
```

## API Documentation

The API documentation is available at `/api/v1/docs` when the application is running. It provides a comprehensive overview of all available endpoints, request/response schemas, and authentication requirements.

## Testing

Run the tests with pytest:

```bash
pytest
```

For test coverage:

```bash
pytest --cov=app
```


## Deployment

The application is containerized and can be deployed to any environment that supports Docker.

For production deployment:

1. Update the `.env` file with production settings
2. Build and deploy the Docker containers
3. Set up a reverse proxy (like Nginx) for SSL termination
4. Configure proper database backups

## License

This project is licensed under the MIT License - see the LICENSE file for details.