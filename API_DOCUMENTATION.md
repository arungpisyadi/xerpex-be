# XerpeX ERP API Documentation

This document provides detailed information about the API endpoints available in the XerpeX ERP system.

## Authentication

All API endpoints (except for login and register) require authentication using JWT tokens.

### Authentication Flow

1. Obtain a JWT token by sending a POST request to `/api/v1/auth/login`
2. Include the token in the Authorization header of subsequent requests:
   `Authorization: Bearer {your_token}`

### Authentication Endpoints

#### Login

```
POST /api/v1/auth/login
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "admin",
    "is_active": true
  }
}
```

#### Register

```
POST /api/v1/auth/register
```

Request body:
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User",
  "role": "staff"
}
```

Response:
```json
{
  "id": 2,
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "staff",
  "is_active": true
}
```

## User Management

### Get Current User

```
GET /api/v1/users/me
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "admin",
  "is_active": true
}
```

### Get All Users

```
GET /api/v1/users/
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

Response:
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "admin",
    "is_active": true
  },
  {
    "id": 2,
    "email": "newuser@example.com",
    "full_name": "New User",
    "role": "staff",
    "is_active": true
  }
]
```

### Get User by ID

```
GET /api/v1/users/{user_id}
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "admin",
  "is_active": true
}
```

### Create User

```
POST /api/v1/users/
```

Request body:
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User",
  "role": "staff"
}
```

Response:
```json
{
  "id": 2,
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "staff",
  "is_active": true
}
```

### Update User

```
PUT /api/v1/users/{user_id}
```

Request body:
```json
{
  "email": "updated@example.com",
  "full_name": "Updated User",
  "role": "admin",
  "is_active": true
}
```

Response:
```json
{
  "id": 2,
  "email": "updated@example.com",
  "full_name": "Updated User",
  "role": "admin",
  "is_active": true
}
```

### Delete User

```
DELETE /api/v1/users/{user_id}
```

Response:
```json
{
  "message": "User deleted successfully"
}
```

## Villa Management

### Get All Villas

```
GET /api/v1/villas/
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

Response:
```json
[
  {
    "id": 1,
    "name": "Luxury Villa",
    "description": "A beautiful luxury villa with ocean view",
    "price_per_night": 250.00,
    "capacity": 4,
    "amenities": ["Pool", "Jacuzzi", "Garden"],
    "is_available": true
  },
  {
    "id": 2,
    "name": "Family Villa",
    "description": "Spacious villa for family gatherings",
    "price_per_night": 350.00,
    "capacity": 8,
    "amenities": ["Pool", "BBQ", "Garden", "Playground"],
    "is_available": true
  }
]
```

### Get Villa by ID

```
GET /api/v1/villas/{villa_id}
```

Response:
```json
{
  "id": 1,
  "name": "Luxury Villa",
  "description": "A beautiful luxury villa with ocean view",
  "price_per_night": 250.00,
  "capacity": 4,
  "amenities": ["Pool", "Jacuzzi", "Garden"],
  "is_available": true
}
```

### Create Villa

```
POST /api/v1/villas/
```

Request body:
```json
{
  "name": "New Villa",
  "description": "A new villa with mountain view",
  "price_per_night": 300.00,
  "capacity": 6,
  "amenities": ["Pool", "Mountain View", "Garden"],
  "is_available": true
}
```

Response:
```json
{
  "id": 3,
  "name": "New Villa",
  "description": "A new villa with mountain view",
  "price_per_night": 300.00,
  "capacity": 6,
  "amenities": ["Pool", "Mountain View", "Garden"],
  "is_available": true
}
```

### Update Villa

```
PUT /api/v1/villas/{villa_id}
```

Request body:
```json
{
  "name": "Updated Villa",
  "description": "Updated description",
  "price_per_night": 350.00,
  "capacity": 6,
  "amenities": ["Pool", "Mountain View", "Garden", "Sauna"],
  "is_available": true
}
```

Response:
```json
{
  "id": 3,
  "name": "Updated Villa",
  "description": "Updated description",
  "price_per_night": 350.00,
  "capacity": 6,
  "amenities": ["Pool", "Mountain View", "Garden", "Sauna"],
  "is_available": true
}
```

### Delete Villa

```
DELETE /api/v1/villas/{villa_id}
```

Response:
```json
{
  "message": "Villa deleted successfully"
}
```

## Booking Management

### Get All Bookings

```
GET /api/v1/bookings/
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)
- `status`: Filter by booking status (optional)

Response:
```json
[
  {
    "id": 1,
    "user_id": 1,
    "villa_id": 1,
    "check_in_date": "2025-08-01",
    "check_out_date": "2025-08-05",
    "total_guests": 3,
    "total_price": 1000.00,
    "status": "confirmed",
    "created_at": "2025-07-15T10:30:00",
    "updated_at": "2025-07-15T10:30:00"
  },
  {
    "id": 2,
    "user_id": 2,
    "villa_id": 2,
    "check_in_date": "2025-08-10",
    "check_out_date": "2025-08-15",
    "total_guests": 6,
    "total_price": 1750.00,
    "status": "pending",
    "created_at": "2025-07-16T14:20:00",
    "updated_at": "2025-07-16T14:20:00"
  }
]
```

### Get Booking by ID

```
GET /api/v1/bookings/{booking_id}
```

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "villa_id": 1,
  "check_in_date": "2025-08-01",
  "check_out_date": "2025-08-05",
  "total_guests": 3,
  "total_price": 1000.00,
  "status": "confirmed",
  "created_at": "2025-07-15T10:30:00",
  "updated_at": "2025-07-15T10:30:00"
}
```

### Create Booking

```
POST /api/v1/bookings/
```

Request body:
```json
{
  "villa_id": 1,
  "check_in_date": "2025-09-01",
  "check_out_date": "2025-09-05",
  "total_guests": 2,
  "special_requests": "Early check-in if possible"
}
```

Response:
```json
{
  "id": 3,
  "user_id": 1,
  "villa_id": 1,
  "check_in_date": "2025-09-01",
  "check_out_date": "2025-09-05",
  "total_guests": 2,
  "total_price": 1000.00,
  "status": "pending",
  "special_requests": "Early check-in if possible",
  "created_at": "2025-07-17T14:30:00",
  "updated_at": "2025-07-17T14:30:00"
}
```

### Update Booking Status

```
PATCH /api/v1/bookings/{booking_id}/status
```

Request body:
```json
{
  "status": "confirmed"
}
```

Response:
```json
{
  "id": 3,
  "user_id": 1,
  "villa_id": 1,
  "check_in_date": "2025-09-01",
  "check_out_date": "2025-09-05",
  "total_guests": 2,
  "total_price": 1000.00,
  "status": "confirmed",
  "special_requests": "Early check-in if possible",
  "created_at": "2025-07-17T14:30:00",
  "updated_at": "2025-07-17T14:35:00"
}
```

### Cancel Booking

```
DELETE /api/v1/bookings/{booking_id}
```

Response:
```json
{
  "message": "Booking cancelled successfully"
}
```

## Payment Management

### Get All Payments

```
GET /api/v1/payments/
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)
- `status`: Filter by payment status (optional)

Response:
```json
[
  {
    "id": 1,
    "booking_id": 1,
    "amount": 1000.00,
    "payment_method": "credit_card",
    "status": "completed",
    "transaction_id": "txn_123456",
    "created_at": "2025-07-15T10:35:00",
    "updated_at": "2025-07-15T10:35:00"
  },
  {
    "id": 2,
    "booking_id": 2,
    "amount": 875.00,
    "payment_method": "bank_transfer",
    "status": "pending",
    "transaction_id": null,
    "created_at": "2025-07-16T14:25:00",
    "updated_at": "2025-07-16T14:25:00"
  }
]
```

### Get Payment by ID

```
GET /api/v1/payments/{payment_id}
```

Response:
```json
{
  "id": 1,
  "booking_id": 1,
  "amount": 1000.00,
  "payment_method": "credit_card",
  "status": "completed",
  "transaction_id": "txn_123456",
  "created_at": "2025-07-15T10:35:00",
  "updated_at": "2025-07-15T10:35:00"
}
```

### Create Payment

```
POST /api/v1/payments/
```

Request body:
```json
{
  "booking_id": 3,
  "amount": 1000.00,
  "payment_method": "credit_card"
}
```

Response:
```json
{
  "id": 3,
  "booking_id": 3,
  "amount": 1000.00,
  "payment_method": "credit_card",
  "status": "pending",
  "transaction_id": null,
  "created_at": "2025-07-17T14:40:00",
  "updated_at": "2025-07-17T14:40:00"
}
```

### Update Payment Status

```
PATCH /api/v1/payments/{payment_id}/status
```

Request body:
```json
{
  "status": "completed",
  "transaction_id": "txn_789012"
}
```

Response:
```json
{
  "id": 3,
  "booking_id": 3,
  "amount": 1000.00,
  "payment_method": "credit_card",
  "status": "completed",
  "transaction_id": "txn_789012",
  "created_at": "2025-07-17T14:40:00",
  "updated_at": "2025-07-17T14:45:00"
}
```

## Reporting

### Occupancy Report

```
GET /api/v1/reports/occupancy
```

Query parameters:
- `start_date`: Start date for the report (YYYY-MM-DD)
- `end_date`: End date for the report (YYYY-MM-DD)

Response:
```json
{
  "start_date": "2025-08-01",
  "end_date": "2025-08-31",
  "total_villas": 3,
  "total_days": 31,
  "total_possible_nights": 93,
  "total_booked_nights": 45,
  "occupancy_rate": 48.39,
  "villa_breakdown": [
    {
      "villa_id": 1,
      "villa_name": "Luxury Villa",
      "booked_nights": 20,
      "occupancy_rate": 64.52
    },
    {
      "villa_id": 2,
      "villa_name": "Family Villa",
      "booked_nights": 15,
      "occupancy_rate": 48.39
    },
    {
      "villa_id": 3,
      "villa_name": "New Villa",
      "booked_nights": 10,
      "occupancy_rate": 32.26
    }
  ]
}
```

### Revenue Report

```
GET /api/v1/reports/revenue
```

Query parameters:
- `start_date`: Start date for the report (YYYY-MM-DD)
- `end_date`: End date for the report (YYYY-MM-DD)
- `group_by`: Group results by 'day', 'week', or 'month' (default: 'month')

Response:
```json
{
  "start_date": "2025-08-01",
  "end_date": "2025-08-31",
  "total_revenue": 15000.00,
  "payment_method_breakdown": {
    "credit_card": 10000.00,
    "bank_transfer": 5000.00
  },
  "villa_breakdown": [
    {
      "villa_id": 1,
      "villa_name": "Luxury Villa",
      "revenue": 5000.00
    },
    {
      "villa_id": 2,
      "villa_name": "Family Villa",
      "revenue": 7000.00
    },
    {
      "villa_id": 3,
      "villa_name": "New Villa",
      "revenue": 3000.00
    }
  ],
  "time_series": [
    {
      "period": "2025-08-01 - 2025-08-07",
      "revenue": 3500.00
    },
    {
      "period": "2025-08-08 - 2025-08-14",
      "revenue": 4200.00
    },
    {
      "period": "2025-08-15 - 2025-08-21",
      "revenue": 3800.00
    },
    {
      "period": "2025-08-22 - 2025-08-31",
      "revenue": 3500.00
    }
  ]
}
```

### Booking Status Report

```
GET /api/v1/reports/booking-status
```

Query parameters:
- `start_date`: Start date for the report (YYYY-MM-DD)
- `end_date`: End date for the report (YYYY-MM-DD)

Response:
```json
{
  "start_date": "2025-08-01",
  "end_date": "2025-08-31",
  "total_bookings": 25,
  "status_breakdown": {
    "confirmed": 15,
    "pending": 5,
    "cancelled": 3,
    "completed": 2
  },
  "cancellation_rate": 12.00
}
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or invalid credentials
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}