# XerpeX ERP System \- Backend Documentation

## 1\. Introduction

This document outlines the complete API contract and database schema for the XerpeX ERP system, which includes features for Booking Management, Calendar Views, Payment Tracking, Villa/Room Management, Reporting, and User System.

---

## 2\. Database Schema (PostgreSQL)

### 2.1 Tables & Relationships

#### Users & Authentication

sql

`CREATE TABLE users (`  
    `id SERIAL PRIMARY KEY,`  
    `username VARCHAR(50) UNIQUE NOT NULL,`  
    `email VARCHAR(100) UNIQUE NOT NULL,`  
    `password_hash VARCHAR(255) NOT NULL,`  
    `full_name VARCHAR(100),`  
    `role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'manager', 'staff')),`  
    `is_active BOOLEAN DEFAULT TRUE,`  
    `last_login TIMESTAMP,`  
    `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,`  
    `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

`CREATE TABLE user_activities (`  
    `id SERIAL PRIMARY KEY,`  
    `user_id INT REFERENCES users(id) ON DELETE CASCADE,`  
    `activity_type VARCHAR(50) NOT NULL,`  
    `description TEXT,`  
    `ip_address VARCHAR(45),`  
    `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

#### Villa & Room Management

sql

`CREATE TABLE villas (`  
    `id SERIAL PRIMARY KEY,`  
    `name VARCHAR(100) NOT NULL,`  
    `description TEXT,`  
    `capacity INT NOT NULL,`  
    `room_type VARCHAR(50) NOT NULL,`  
    `base_price DECIMAL(10, 2) NOT NULL,`  
    `is_active BOOLEAN DEFAULT TRUE,`  
    `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,`  
    `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

`CREATE TABLE villa_availability (`  
    `id SERIAL PRIMARY KEY,`  
    `villa_id INT REFERENCES villas(id) ON DELETE CASCADE,`  
    `date DATE NOT NULL,`  
    `is_available BOOLEAN DEFAULT TRUE,`  
    `blocked_reason TEXT,`  
    `updated_by INT REFERENCES users(id) ON DELETE SET NULL,`  
    `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,`  
    `UNIQUE(villa_id, date)`  
`);`

#### Booking Management

sql

`CREATE TABLE bookings (`  
    `id SERIAL PRIMARY KEY,`  
    `booking_code VARCHAR(20) UNIQUE NOT NULL,`  
    `guest_name VARCHAR(100) NOT NULL,`  
    `guest_email VARCHAR(100),`  
    `guest_phone VARCHAR(20),`  
    `check_in DATE NOT NULL,`  
    `check_out DATE NOT NULL,`  
    `total_pax INT NOT NULL,`  
    `status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'confirmed', 'ongoing', 'completed', 'cancelled')),`  
    `notes TEXT,`  
    `created_by INT REFERENCES users(id) ON DELETE SET NULL,`  
    `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,`  
    `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

`CREATE TABLE booking_villas (`  
    `id SERIAL PRIMARY KEY,`  
    `booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,`  
    `villa_id INT REFERENCES villas(id) ON DELETE CASCADE,`  
    `assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

`CREATE TABLE booking_packages (`  
    `id SERIAL PRIMARY KEY,`  
    `booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,`  
    `package_name VARCHAR(100) NOT NULL,`  
    `package_price DECIMAL(10, 2) NOT NULL,`  
    `notes TEXT`  
`);`

`CREATE TABLE booking_addons (`  
    `id SERIAL PRIMARY KEY,`  
    `booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,`  
    `service_name VARCHAR(100) NOT NULL,`  
    `service_price DECIMAL(10, 2) NOT NULL,`  
    `quantity INT DEFAULT 1`  
`);`

#### Payment Management

sql

`CREATE TABLE payments (`  
    `id SERIAL PRIMARY KEY,`  
    `booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,`  
    `amount DECIMAL(10, 2) NOT NULL,`  
    `payment_method VARCHAR(50) NOT NULL,`  
    `payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,`  
    `status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'paid', 'failed', 'refunded')),`  
    `notes TEXT,`  
    `recorded_by INT REFERENCES users(id) ON DELETE SET NULL`  
`);`

`CREATE TABLE invoices (`  
    `id SERIAL PRIMARY KEY,`  
    `booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,`  
    `invoice_number VARCHAR(50) UNIQUE NOT NULL,`  
    `total_amount DECIMAL(10, 2) NOT NULL,`  
    `due_date DATE NOT NULL,`  
    `status VARCHAR(20) NOT NULL CHECK (status IN ('unpaid', 'paid', 'overdue')),`  
    `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

---

## 3\. API Contract (RESTful)

### 3.1 Authentication & Users

| Endpoint | Method | Description | Request Body | Response |
| :---- | :---- | :---- | :---- | :---- |
| `/auth/login` | POST | User login | `{ email, password }` | `{ token, user }` |
| `/auth/logout` | POST | User logout | \- | `{ success: true }` |
| `/users` | GET | List all users | \- | `[ { id, username, role } ]` |
| `/users/{id}` | GET | Get user details | \- | `{ id, username, role, last_login }` |

### 3.2 Villa Management

| Endpoint | Method | Description | Request Body | Response |
| :---- | :---- | :---- | :---- | :---- |
| `/villas` | GET | List all villas | \- | `[ { id, name, capacity, base_price } ]` |
| `/villas/{id}` | GET | Get villa details | \- | `{ id, name, description, capacity, base_price }` |
| `/villas/availability` | GET | Check availability | `{ villa_id, check_in, check_out }` | `{ is_available }` |

### 3.3 Booking Management

| Endpoint | Method | Description | Request Body | Response |
| :---- | :---- | :---- | :---- | :---- |
| `/bookings` | POST | Create booking | `{ guest_name, check_in, check_out, pax, villa_id }` | `{ booking_id, booking_code }` |
| `/bookings/{id}` | GET | Get booking details | \- | `{ booking_code, guest_name, status, check_in, check_out }` |
| `/bookings/{id}/status` | PATCH | Update booking status | `{ status }` | `{ success: true }` |

### 3.4 Payment Management

| Endpoint | Method | Description | Request Body | Response |
| :---- | :---- | :---- | :---- | :---- |
| `/payments` | POST | Record payment | `{ booking_id, amount, method }` | `{ payment_id, status }` |
| `/invoices/{booking_id}` | GET | Generate invoice | \- | `{ invoice_number, total, due_date }` |

### 3.5 Reporting

| Endpoint | Method | Description | Query Params | Response |
| :---- | :---- | :---- | :---- | :---- |
| `/reports/bookings` | GET | Booking reports | `start_date, end_date` | `{ total_bookings, revenue }` |
| `/reports/villa-utilization` | GET | Villa utilization | `month, year` | `[ { villa_name, occupancy_rate } ]` |

---

## 4\. Additional Notes

* Security: JWT-based authentication.  
* Error Handling: Standard HTTP status codes (`200 OK`, `400 Bad Request`, `401 Unauthorized`, `404 Not Found`).  
* Validation: Request payload validation for required fields.  
* Pagination: Applied to large datasets (e.g., `/bookings`).