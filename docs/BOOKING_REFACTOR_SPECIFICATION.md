# Booking Module Refactor Design Specification

**Version:** 1.0  
**Date:** 2025-11-03  
**Author:** System Architect  
**Status:** Design Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Target State Design](#target-state-design)
4. [Database Schema Changes](#database-schema-changes)
5. [Migration Strategy](#migration-strategy)
6. [Model Layer Changes](#model-layer-changes)
7. [Schema Layer Changes](#schema-layer-changes)
8. [Service Layer Changes](#service-layer-changes)
9. [Breaking Changes and Considerations](#breaking-changes-and-considerations)
10. [Implementation Checklist](#implementation-checklist)

---

## 1. Executive Summary

This document outlines the comprehensive refactoring of the bookings module to align with the quotes module architecture. The refactor includes database restructuring, model updates, schema updates, and service layer enhancements to create a unified, maintainable system pattern.

**Key Objectives:**
- Align bookings structure with quotes module pattern
- Introduce flexible item-based pricing model
- Add comprehensive audit trail with booking history
- Maintain villa selection functionality unique to bookings
- Support customer linking and user isolation
- Improve financial tracking with totals and tax calculations

---

## 2. Current State Analysis

### 2.1 Current Booking Database Schema

#### Bookings Table
```sql
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    booking_code VARCHAR(20) UNIQUE NOT NULL,
    guest_name VARCHAR(100) NOT NULL,
    guest_email VARCHAR(100),
    guest_phone VARCHAR(20),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    total_pax INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    notes TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### BookingVilla Table (Already Exists - Will Keep)
```sql
CREATE TABLE booking_villas (
    id INTEGER PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    villa_id INTEGER NOT NULL REFERENCES villas(id) ON DELETE CASCADE,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### BookingPackage Table (Will Be Dropped)
```sql
CREATE TABLE booking_packages (
    id INTEGER PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    package_name VARCHAR(100) NOT NULL,
    package_price NUMERIC(10, 2) NOT NULL,
    notes TEXT
);
```

#### BookingAddon Table (Will Be Dropped)
```sql
CREATE TABLE booking_addons (
    id INTEGER PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    service_name VARCHAR(100) NOT NULL,
    service_price NUMERIC(10, 2) NOT NULL,
    quantity INTEGER DEFAULT 1
);
```

### 2.2 Current Model Relationships

- **Booking** → BookingVilla (one-to-many)
- **Booking** → BookingPackage (one-to-many)
- **Booking** → BookingAddon (one-to-many)
- **Booking** → User (created_by, many-to-one)

### 2.3 Current Issues

1. **Inconsistent Architecture:** Bookings use different structure than quotes
2. **No Customer Linking:** Guest information is embedded, not linked to customers table
3. **No User Isolation:** Missing user_id field for role-based access control
4. **Limited Financial Tracking:** No subtotal, tax, or payment tracking fields
5. **No Audit Trail:** No history table for tracking changes
6. **Inflexible Pricing:** Separate tables for packages/addons instead of unified items
7. **Old Decimal Precision:** Using NUMERIC(10,2) instead of NUMERIC(15,2)
8. **No Pax Tracking:** Cannot track per-item passenger counts

---

## 3. Target State Design

### 3.1 Design Principles

1. **Consistency:** Mirror the quotes module structure
2. **Flexibility:** Support any type of items (packages, services, addons)
3. **Traceability:** Complete audit trail with history tracking
4. **Integration:** Link to customers table for CRM integration
5. **Security:** User isolation and role-based access control
6. **Uniqueness:** Maintain villa selection feature specific to bookings

### 3.2 Target Architecture

```
Booking (main record)
├── BookingItem (flexible line items)
│   └── Package (reference)
├── BookingVilla (villa assignments - unique to bookings)
│   └── Villa (reference)
├── BookingHistory (audit trail)
├── Customer (linked record)
├── User (owner)
└── Payments (financial records)
```

---

## 4. Database Schema Changes

### 4.1 Restructured Bookings Table

```sql
CREATE TABLE bookings (
    -- Primary Key
    id INTEGER PRIMARY KEY,
    
    -- Foreign Keys
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    sales_person_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Booking Identifiers
    booking_code VARCHAR(50) UNIQUE NOT NULL,
    
    -- Dates
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Guest Information (kept for legacy compatibility and walk-ins)
    guest_name VARCHAR(100),
    guest_email VARCHAR(100),
    guest_phone VARCHAR(20),
    
    -- Additional Information
    total_pax INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    
    -- Financial Fields
    total NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    tax_total NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    amount_paid NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    amount_due NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    
    -- Audit Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_bookings_booking_code (booking_code),
    INDEX idx_bookings_user_id (user_id),
    INDEX idx_bookings_customer_id (customer_id),
    INDEX idx_bookings_check_in (check_in),
    INDEX idx_bookings_status (status),
    
    -- Constraints
    CONSTRAINT check_booking_status CHECK (
        status IN ('pending', 'confirmed', 'checked_in', 'checked_out', 'completed', 'cancelled')
    ),
    CONSTRAINT check_booking_dates CHECK (check_out > check_in)
);
```

### 4.2 New Booking Items Table

```sql
CREATE TABLE booking_items (
    -- Primary Key
    id INTEGER PRIMARY KEY,
    
    -- Foreign Keys
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    package_id INTEGER NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    
    -- Item Details
    pax INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(15, 2) NOT NULL,
    discount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    line_total NUMERIC(15, 2) NOT NULL,
    
    -- Audit Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_booking_items_booking_id (booking_id),
    INDEX idx_booking_items_package_id (package_id),
    
    -- Constraints
    CONSTRAINT check_pax_positive CHECK (pax >= 1),
    CONSTRAINT check_unit_price_non_negative CHECK (unit_price >= 0),
    CONSTRAINT check_discount_non_negative CHECK (discount >= 0)
);
```

### 4.3 New Booking History Table

```sql
CREATE TABLE booking_history (
    -- Primary Key
    id INTEGER PRIMARY KEY,
    
    -- Foreign Keys
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Change Details
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(50) NOT NULL,
    
    -- Audit Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_booking_history_booking_id (booking_id),
    INDEX idx_booking_history_user_id (user_id),
    INDEX idx_booking_history_created_at (created_at),
    
    -- Constraints
    CONSTRAINT check_change_type CHECK (
        change_type IN ('created', 'status_change', 'field_update', 'item_added', 
                       'item_removed', 'villa_added', 'villa_removed', 'payment_received')
    )
);
```

### 4.4 Booking Villas Table (Updated)

```sql
CREATE TABLE booking_villas (
    -- Primary Key
    id INTEGER PRIMARY KEY,
    
    -- Foreign Keys
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    villa_id INTEGER NOT NULL REFERENCES villas(id) ON DELETE CASCADE,
    
    -- Villa-specific Details
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    nightly_rate NUMERIC(15, 2) NOT NULL,
    total_nights INTEGER NOT NULL,
    villa_total NUMERIC(15, 2) NOT NULL,
    
    -- Audit Fields
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_booking_villas_booking_id (booking_id),
    INDEX idx_booking_villas_villa_id (villa_id),
    
    -- Constraints
    CONSTRAINT check_villa_dates CHECK (check_out > check_in),
    CONSTRAINT check_nightly_rate_non_negative CHECK (nightly_rate >= 0)
);
```

---

## 5. Migration Strategy

### 5.1 Migration File Structure

Create migration: `020_refactor_bookings_module.py`

### 5.2 Migration Steps

#### Step 1: Pre-Migration Validation
```python
# Verify no active bookings with critical data
# Check for any foreign key dependencies
# Create backup of existing data
```

#### Step 2: Create New Tables
```python
def upgrade():
    # 1. Create booking_items table
    op.create_table(
        'booking_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('pax', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('discount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('line_total', sa.Numeric(15, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_booking_items_id', 'booking_items', ['id'])
    op.create_index('ix_booking_items_booking_id', 'booking_items', ['booking_id'])
    
    # 2. Create booking_history table
    op.create_table(
        'booking_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('change_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "change_type IN ('created', 'status_change', 'field_update', 'item_added', " +
            "'item_removed', 'villa_added', 'villa_removed', 'payment_received')",
            name='check_booking_history_change_type'
        )
    )
    op.create_index('ix_booking_history_id', 'booking_history', ['id'])
    op.create_index('ix_booking_history_booking_id', 'booking_history', ['booking_id'])
    op.create_index('ix_booking_history_created_at', 'booking_history', ['created_at'])
```

#### Step 3: Update Bookings Table
```python
def upgrade():
    # Add new columns to bookings table
    op.add_column('bookings', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('sales_person_id', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('total', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
    op.add_column('bookings', sa.Column('tax_total', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
    op.add_column('bookings', sa.Column('amount_paid', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
    op.add_column('bookings', sa.Column('amount_due', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
    
    # Migrate existing data
    # Set user_id to created_by where available, otherwise default to admin user (id=1)
    op.execute("UPDATE bookings SET user_id = COALESCE(created_by, 1)")
    
    # Create a default customer for existing bookings without customer link
    # or map based on guest_email if customer exists
    op.execute("""
        UPDATE bookings b
        LEFT JOIN customers c ON b.guest_email = c.email
        SET b.customer_id = COALESCE(c.id, 1)
    """)
    
    # Calculate totals from packages and addons
    op.execute("""
        UPDATE bookings b
        SET b.total = COALESCE(
            (SELECT SUM(bp.package_price) FROM booking_packages bp WHERE bp.booking_id = b.id), 0
        ) + COALESCE(
            (SELECT SUM(ba.service_price * ba.quantity) FROM booking_addons ba WHERE ba.booking_id = b.id), 0
        )
    """)
    
    # Set amount_due = total for all existing bookings
    op.execute("UPDATE bookings SET amount_due = total")
    
    # Calculate amount_paid from payments table
    op.execute("""
        UPDATE bookings b
        SET b.amount_paid = COALESCE(
            (SELECT SUM(p.amount) FROM payments p WHERE p.booking_id = b.id AND p.status = 'paid'), 0
        )
    """)
    
    # Make columns non-nullable after data migration
    op.alter_column('bookings', 'user_id', nullable=False)
    op.alter_column('bookings', 'customer_id', nullable=False)
    op.alter_column('bookings', 'total', nullable=False)
    op.alter_column('bookings', 'tax_total', nullable=False)
    op.alter_column('bookings', 'amount_paid', nullable=False)
    op.alter_column('bookings', 'amount_due', nullable=False)
    
    # Add foreign key constraints
    op.create_foreign_key('fk_bookings_user_id', 'bookings', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_bookings_customer_id', 'bookings', 'customers', ['customer_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_bookings_sales_person_id', 'bookings', 'users', ['sales_person_id'], ['id'], ondelete='SET NULL')
    
    # Update status constraint
    op.drop_constraint('check_booking_status', 'bookings', type_='check')
    op.create_check_constraint(
        'check_booking_status',
        'bookings',
        "status IN ('pending', 'confirmed', 'checked_in', 'checked_out', 'completed', 'cancelled')"
    )
```

#### Step 4: Migrate Data to booking_items
```python
def upgrade():
    # Migrate booking_packages to booking_items
    op.execute("""
        INSERT INTO booking_items (booking_id, package_id, pax, unit_price, discount, line_total, created_at)
        SELECT 
            bp.booking_id,
            COALESCE(p.id, 1) as package_id,  -- Link to actual package or use default
            b.total_pax,
            bp.package_price,
            0.00,
            bp.package_price,
            NOW()
        FROM booking_packages bp
        JOIN bookings b ON bp.booking_id = b.id
        LEFT JOIN packages p ON p.name = bp.package_name
    """)
    
    # Migrate booking_addons to booking_items
    op.execute("""
        INSERT INTO booking_items (booking_id, package_id, pax, unit_price, discount, line_total, created_at)
        SELECT 
            ba.booking_id,
            COALESCE(p.id, 1) as package_id,  -- Link to actual package or use default
            ba.quantity,
            ba.service_price,
            0.00,
            ba.service_price * ba.quantity,
            NOW()
        FROM booking_addons ba
        LEFT JOIN packages p ON p.name = ba.service_name
    """)
```

#### Step 5: Update booking_villas Table
```python
def upgrade():
    # Add new columns
    op.add_column('booking_villas', sa.Column('check_in', sa.Date(), nullable=True))
    op.add_column('booking_villas', sa.Column('check_out', sa.Date(), nullable=True))
    op.add_column('booking_villas', sa.Column('nightly_rate', sa.Numeric(15, 2), nullable=True))
    op.add_column('booking_villas', sa.Column('total_nights', sa.Integer(), nullable=True))
    op.add_column('booking_villas', sa.Column('villa_total', sa.Numeric(15, 2), nullable=True))
    op.add_column('booking_villas', sa.Column('assigned_by', sa.Integer(), nullable=True))
    
    # Migrate data from bookings table
    op.execute("""
        UPDATE booking_villas bv
        JOIN bookings b ON bv.booking_id = b.id
        JOIN villas v ON bv.villa_id = v.id
        SET 
            bv.check_in = b.check_in,
            bv.check_out = b.check_out,
            bv.nightly_rate = v.base_price,
            bv.total_nights = DATEDIFF(b.check_out, b.check_in),
            bv.villa_total = v.base_price * DATEDIFF(b.check_out, b.check_in),
            bv.assigned_by = b.user_id
    """)
    
    # Make columns non-nullable
    op.alter_column('booking_villas', 'check_in', nullable=False)
    op.alter_column('booking_villas', 'check_out', nullable=False)
    op.alter_column('booking_villas', 'nightly_rate', nullable=False)
    op.alter_column('booking_villas', 'total_nights', nullable=False)
    op.alter_column('booking_villas', 'villa_total', nullable=False)
    
    # Add foreign key for assigned_by
    op.create_foreign_key('fk_booking_villas_assigned_by', 'booking_villas', 'users', 
                         ['assigned_by'], ['id'], ondelete='SET NULL')
```

#### Step 6: Create Initial History Records
```python
def upgrade():
    # Create initial history records for existing bookings
    op.execute("""
        INSERT INTO booking_history (booking_id, user_id, field_name, old_value, new_value, change_type, created_at)
        SELECT 
            id,
            user_id,
            'status',
            NULL,
            status,
            'created',
            created_at
        FROM bookings
    """)
```

#### Step 7: Drop Old Tables
```python
def upgrade():
    # Drop old tables
    op.drop_table('booking_addons')
    op.drop_table('booking_packages')
```

### 5.3 Rollback Strategy

```python
def downgrade():
    # 1. Recreate old tables
    op.create_table('booking_packages', ...)
    op.create_table('booking_addons', ...)
    
    # 2. Migrate data back from booking_items
    # (Implementation details...)
    
    # 3. Remove new columns from bookings
    op.drop_constraint('fk_bookings_user_id', 'bookings', type_='foreignkey')
    op.drop_constraint('fk_bookings_customer_id', 'bookings', type_='foreignkey')
    op.drop_column('bookings', 'user_id')
    op.drop_column('bookings', 'customer_id')
    # ... (remove all new columns)
    
    # 4. Drop new tables
    op.drop_table('booking_history')
    op.drop_table('booking_items')
```

---

## 6. Model Layer Changes

### 6.1 Updated Booking Model

```python
"""
app/models/booking.py
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Booking(Base):
    """Booking model for accommodation booking system"""
    __tablename__ = "bookings"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    sales_person_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Booking Identifiers
    booking_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Dates
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    
    # Status
    status = Column(String(20), nullable=False, default="pending")
    
    # Guest Information (legacy compatibility)
    guest_name = Column(String(100), nullable=True)
    guest_email = Column(String(100), nullable=True)
    guest_phone = Column(String(20), nullable=True)
    
    # Additional Information
    total_pax = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    
    # Financial Fields
    total = Column(Numeric(15, 2), nullable=False, default=0.00)
    tax_total = Column(Numeric(15, 2), nullable=False, default=0.00)
    amount_paid = Column(Numeric(15, 2), nullable=False, default=0.00)
    amount_due = Column(Numeric(15, 2), nullable=False, default=0.00)
    
    # Audit Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")
    sales_person = relationship("User", foreign_keys=[sales_person_id], back_populates="sales_person_bookings")
    items = relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")
    villas = relationship("BookingVilla", back_populates="booking", cascade="all, delete-orphan")
    history = relationship("BookingHistory", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'checked_in', 'checked_out', 'completed', 'cancelled')",
            name="check_booking_status"
        ),
        CheckConstraint(
            "check_out > check_in",
            name="check_booking_dates"
        ),
        {"sqlite_autoincrement": True},
    )


class BookingItem(Base):
    """Booking item model for booking line items"""
    __tablename__ = "booking_items"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)
    pax = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(15, 2), nullable=False)
    discount = Column(Numeric(15, 2), nullable=False, default=0.00)
    line_total = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", back_populates="items")
    package = relationship("Package", back_populates="booking_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("pax >= 1", name="check_booking_item_pax"),
        CheckConstraint("unit_price >= 0", name="check_booking_item_unit_price"),
        CheckConstraint("discount >= 0", name="check_booking_item_discount"),
        {"sqlite_autoincrement": True},
    )


class BookingVilla(Base):
    """Booking villa model for villa assignments"""
    __tablename__ = "booking_villas"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    nightly_rate = Column(Numeric(15, 2), nullable=False)
    total_nights = Column(Integer, nullable=False)
    villa_total = Column(Numeric(15, 2), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    booking = relationship("Booking", back_populates="villas")
    villa = relationship("Villa", back_populates="bookings")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    # Constraints
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="check_booking_villa_dates"),
        CheckConstraint("nightly_rate >= 0", name="check_booking_villa_rate"),
        {"sqlite_autoincrement": True},
    )


class BookingHistory(Base):
    """Booking history model for audit trail"""
    __tablename__ = "booking_history"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    booking = relationship("Booking", back_populates="history")
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('created', 'status_change', 'field_update', 'item_added', " +
            "'item_removed', 'villa_added', 'villa_removed', 'payment_received')",
            name="check_booking_history_change_type"
        ),
        {"sqlite_autoincrement": True},
    )
```

### 6.2 Related Model Updates

**User Model** - Add relationships:
```python
# In app/models/user.py
bookings = relationship("Booking", foreign_keys="Booking.user_id", back_populates="user")
sales_person_bookings = relationship("Booking", foreign_keys="Booking.sales_person_id", back_populates="sales_person")
```

**Customer Model** - Add relationship:
```python
# In app/models/customer.py
bookings = relationship("Booking", back_populates="customer")
```

**Package Model** - Add relationship:
```python
# In app/models/package.py
booking_items = relationship("BookingItem", back_populates="package")
```

**Villa Model** - Update relationship:
```python
# In app/models/villa.py
# Change from:
bookings = relationship("BookingVilla", back_populates="villa")
# No change needed, relationship already correct
```

---

## 7. Schema Layer Changes

### 7.1 Booking Item Schemas

```python
"""
app/schemas/booking.py - Item schemas
"""
from decimal import Decimal
from pydantic import BaseModel, condecimal, validator, Field
from typing import Optional
from datetime import datetime


class BookingItemBase(BaseModel):
    """Base booking item schema"""
    package_id: int
    unit_price: condecimal(max_digits=15, decimal_places=2)
    discount: condecimal(max_digits=15, decimal_places=2) = Decimal('0.00')
    pax: int = 1
    line_total: condecimal(max_digits=15, decimal_places=2)
    
    @validator('pax')
    def validate_pax(cls, v):
        if v < 1:
            raise ValueError('pax must be at least 1')
        return v


class BookingItemCreate(BookingItemBase):
    """Booking item creation schema"""
    pass


class BookingItemUpdate(BaseModel):
    """Booking item update schema"""
    package_id: Optional[int] = None
    unit_price: Optional[condecimal(max_digits=15, decimal_places=2)] = None
    discount: Optional[condecimal(max_digits=15, decimal_places=2)] = None
    pax: Optional[int] = None
    line_total: Optional[condecimal(max_digits=15, decimal_places=2)] = None


class BookingItemInDB(BookingItemBase):
    """Booking item in database schema"""
    id: int
    booking_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookingItem(BookingItemInDB):
    """Booking item schema for API responses"""
    package: Optional[dict] = None  # Will be populated with Package schema
    
    class Config:
        from_attributes = True
```

### 7.2 Booking Villa Schemas

```python
"""
app/schemas/booking.py - Villa schemas
"""
from datetime import date


class BookingVillaBase(BaseModel):
    """Base booking villa schema"""
    villa_id: int
    check_in: date
    check_out: date
    nightly_rate: condecimal(max_digits=15, decimal_places=2)
    total_nights: int
    villa_total: condecimal(max_digits=15, decimal_places=2)


class BookingVillaCreate(BaseModel):
    """Booking villa creation schema (simplified)"""
    villa_id: int


class BookingVillaInDB(BookingVillaBase):
    """Booking villa in database schema"""
    id: int
    booking_id: int
    assigned_at: datetime
    assigned_by: Optional[int] = None
    
    class Config:
        from_attributes = True


class BookingVilla(BookingVillaInDB):
    """Booking villa schema for API responses"""
    villa: Optional[dict] = None  # Will be populated with Villa schema
    
    class Config:
        from_attributes = True
```

### 7.3 Booking History Schemas

```python
"""
app/schemas/booking.py - History schemas
"""
from typing import Literal

BookingChangeType = Literal[
    'created', 'status_change', 'field_update', 'item_added',
    'item_removed', 'villa_added', 'villa_removed', 'payment_received'
]


class BookingHistoryBase(BaseModel):
    """Base booking history schema"""
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_type: BookingChangeType


class BookingHistoryCreate(BookingHistoryBase):
    """Booking history creation schema"""
    booking_id: int
    user_id: int


class BookingHistory(BookingHistoryBase):
    """Booking history schema"""
    id: int
    booking_id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### 7.4 Main Booking Schemas

```python
"""
app/schemas/booking.py - Main booking schemas
"""
from datetime import date
from typing import List, Optional
from enum import Enum


class BookingStatus(str, Enum):
    """Booking status enumeration"""
    pending = "pending"
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    completed = "completed"
    cancelled = "cancelled"


class BookingBase(BaseModel):
    """Base booking schema"""
    customer_id: int
    check_in: date
    check_out: date
    total_pax: int = 1
    status: BookingStatus = BookingStatus.pending
    notes: Optional[str] = None
    sales_person_id: Optional[int] = None
    
    # Legacy guest fields (optional)
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    
    @validator('check_out')
    def validate_check_out(cls, v, values):
        if 'check_in' in values and v <= values['check_in']:
            raise ValueError('check_out must be after check_in')
        return v
    
    @validator('guest_phone')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            return sanitize_phone_number(v)
        return v


class BookingCreate(BookingBase):
    """Booking creation schema"""
    villas: List[BookingVillaCreate] = []
    items: List[BookingItemCreate] = []


class BookingUpdate(BaseModel):
    """Booking update schema"""
    customer_id: Optional[int] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    total_pax: Optional[int] = None
    status: Optional[BookingStatus] = None
    notes: Optional[str] = None
    sales_person_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    items: Optional[List[BookingItemCreate]] = None
    
    @validator('guest_phone')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            return sanitize_phone_number(v)
        return v


class BookingStatusUpdate(BaseModel):
    """Booking status update schema"""
    status: BookingStatus


class BookingInDB(BookingBase):
    """Booking in database schema"""
    id: int
    user_id: int
    booking_code: str
    total: condecimal(max_digits=15, decimal_places=2)
    tax_total: condecimal(max_digits=15, decimal_places=2)
    amount_paid: condecimal(max_digits=15, decimal_places=2)
    amount_due: condecimal(max_digits=15, decimal_places=2)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Booking(BookingInDB):
    """Booking schema for API responses"""
    customer: Optional[dict] = None  # Customer schema
    items: List[BookingItem] = []
    villas: List[BookingVilla] = []
    
    class Config:
        from_attributes = True


class BookingDetail(Booking):
    """Detailed booking schema with history"""
    history: List[BookingHistory] = []


class BookingSummary(BaseModel):
    """Booking summary schema for lists"""
    id: int
    booking_code: str
    customer_name: str
    check_in: date
    check_out: date
    status: BookingStatus
    total: condecimal(max_digits=15, decimal_places=2)
    amount_due: condecimal(max_digits=15, decimal_places=2)
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    """Response schema for booking list endpoint"""
    bookings: List[Booking]
    total: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True
```

---

## 8. Service Layer Changes

### 8.1 Core Service Functions

```python
"""
app/services/booking.py - Core functions outline
"""

# READ Operations
def get_booking(db: Session, booking_id: int, current_user: User) -> Optional[Booking]:
    """Get booking with user isolation"""
    # Apply user filter based on role
    # Load relationships (customer, items, villas)
    pass

def get_bookings(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    status: Optional[BookingStatus] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    check_in_from: Optional[date] = None,
    check_in_to: Optional[date] = None,
    villa_id: Optional[int] = None
) -> List[Booking]:
    """Get bookings with filtering and user isolation"""
    pass

# CREATE Operations
def create_booking(
    db: Session,
    booking: BookingCreate,
    current_user: User
) -> Booking:
    """
    Create new booking with items and villas
    - Validate customer exists and accessible
    - Generate unique booking_code
    - Check villa availability
    - Create booking items
    - Assign villas
    - Calculate totals
    - Create history record
    - Update villa availability
    """
    pass

# UPDATE Operations
def update_booking(
    db: Session,
    booking_id: int,
    booking_update: BookingUpdate,
    current_user: User
) -> Booking:
    """
    Update booking with business rules
    - Check booking ownership/access
    - Validate status transitions
    - Update items if provided
    - Recalculate totals
    - Create history records for changes
    """
    pass

def update_booking_status(
    db: Session,
    booking_id: int,
    status_update: BookingStatusUpdate,
    current_user: User
) -> Booking:
    """
    Update booking status with workflow validation
    - Validate status transitions
    - Create history record
    """
    pass

# DELETE Operations
def delete_booking(
    db: Session,
    booking_id: int,
    current_user: User
) -> bool:
    """
    Delete booking (only for specific statuses)
    - Check ownership/access
    - Validate booking can be deleted
    - Free villa availability
    - Cascade delete items, villas, history
    """
    pass

# ITEM Operations
def add_booking_item(
    db: Session,
    booking_id: int,
    item: BookingItemCreate,
    current_user: User
) -> BookingItem:
    """Add item to booking and recalculate totals"""
    pass

def update_booking_item(
    db: Session,
    booking_id: int,
    item_id: int,
    item_update: BookingItemUpdate,
    current_user: User
) -> BookingItem:
    """Update booking item and recalculate totals"""
    pass

def remove_booking_item(
    db: Session,
    booking_id: int,
    item_id: int,
    current_user: User
) -> bool:
    """Remove item from booking and recalculate totals"""
    pass

# VILLA Operations
def add_booking_villa(
    db: Session,
    booking_id: int,
    villa: BookingVillaCreate,
    current_user: User
) -> BookingVilla:
    """
    Add villa to booking
    - Check villa availability
    - Calculate villa totals
    - Update villa availability calendar
    - Create history record
    """
    pass

def remove_booking_villa(
    db: Session,
    booking_id: int,
    villa_id: int,
    current_user: User
) -> bool:
    """
    Remove villa from booking
    - Free villa availability
    - Recalculate totals
    - Create history record
    """
    pass

# CALCULATION Operations
def calculate_booking_totals(
    db: Session,
    items: List[BookingItemCreate],
    villas: List[BookingVillaCreate],
    current_user: User,
    tax_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Calculate booking totals including taxes
    Returns: {subtotal, tax_total, total, tax_breakdown}
    """
    pass

def recalculate_booking_totals(
    db: Session,
    booking_id: int,
    current_user: User
) -> Booking:
    """Recalculate and update booking totals"""
    pass

# HISTORY Operations
def create_booking_history(
    db: Session,
    booking_id: int,
    user_id: int,
    field_name: str,
    old_value: Optional[str],
    new_value: Optional[str],
    change_type: str
) -> BookingHistory:
    """Create booking history record"""
    pass

def get_booking_history(
    db: Session,
    booking_id: int,
    current_user: User
) -> List[BookingHistory]:
    """Get booking history with user details"""
    pass

# STATISTICS Operations
def get_booking_statistics(
    db: Session,
    current_user: User,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    """Get booking statistics for dashboard"""
    pass

# VALIDATION Operations
def validate_booking_dates(
    db: Session,
    check_in: date,
    check_out: date,
    villa_ids: List[int],
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, List[str]]:
    """
    Validate booking dates and villa availability
    Returns: (is_valid, error_messages)
    """
    pass
```

### 8.2 Key Service Implementation Notes

1. **User Isolation:** All read operations must use `get_user_filter_condition()` from `app.utils.security`
2. **History Tracking:** All modifications must create history records
3. **Total Calculation:** Implement automatic total calculation on item/villa changes
4. **Villa Availability:** Update `villa_availability` table on villa assignment/removal
5. **Status Workflow:** Implement status transition validation similar to quotes
6. **Transaction Safety:** Use database transactions for complex operations

---

## 9. Breaking Changes and Considerations

### 9.1 API Breaking Changes

1. **Endpoint Structure Changes:**
   - `POST /bookings` - Request body changed to use `items` instead of `packages`/`addons`
   - `GET /bookings/{id}` - Response structure includes new fields
   - Villa assignment now requires check-in/check-out dates

2. **Field Changes:**
   - `created_by` → integrated into `user_id` with different semantics
   - New required fields: `customer_id`, `user_id`
   - New financial fields: `amount_paid`, `amount_due`

3. **Removed Endpoints:**
   - `POST /bookings/{id}/packages` - Replace with `/bookings/{id}/items`
   - `POST /bookings/{id}/addons` - Replace with `/bookings/{id}/items`

### 9.2 Data Migration Risks

1. **Customer Mapping:** Existing bookings without customer links need default customer
2. **Package Mapping:** Package names in `booking_packages` may not match `packages` table
3. **Financial Data:** Historical payment data must be preserved correctly
4. **Villa Availability:** All existing bookings must properly block availability

### 9.3 Backward Compatibility

1. **Guest Fields:** Kept in schema for backward compatibility and walk-in guests
2. **Booking Code:** Format remains the same
3. **Status Values:** Extended but old values remain valid

### 9.4 Testing Requirements

1. **Migration Testing:**
   - Test with various booking states (pending, confirmed, completed, cancelled)
   - Test with bookings having packages, addons, both, or neither
   - Test with multiple villas per booking
   - Test payment history preservation

2. **API Testing:**
   - Test all CRUD operations with new schemas
   - Test user isolation for different roles
   - Test villa availability updates
   - Test history tracking

3. **Integration Testing:**
   - Test interaction with payments module
   - Test interaction with customers module
   - Test interaction with villas module
   - Test interaction with packages module

---

## 10. Implementation Checklist

### Phase 1: Database Migration
- [ ] Create migration file `020_refactor_bookings_module.py`
- [ ] Test migration on development database
- [ ] Test rollback procedure
- [ ] Verify data integrity after migration
- [ ] Test on staging environment
- [ ] Create database backup before production migration

### Phase 2: Model Layer
- [ ] Update `app/models/booking.py` with new models
- [ ] Add relationships to User model
- [ ] Add relationships to Customer model
- [ ] Add relationships to Package model
- [ ] Update Villa model relationships if needed
- [ ] Test model imports and relationships

### Phase 3: Schema Layer
- [ ] Update `app/schemas/booking.py` with new schemas
- [ ] Add validation rules
- [ ] Test schema serialization/deserialization
- [ ] Update API documentation

### Phase 4: Service Layer
- [ ] Refactor `app/services/booking.py`
- [ ] Implement user isolation
- [ ] Implement history tracking
- [ ] Implement totals calculation
- [ ] Implement villa availability management
- [ ] Add comprehensive error handling
- [ ] Write unit tests for all service functions

### Phase 5: Controller Layer
- [ ] Update `app/controllers/booking.py` endpoints
- [ ] Update request/response handling
- [ ] Add new endpoints for items management
- [ ] Add history endpoint
- [ ] Update documentation

### Phase 6: Testing
- [ ] Write migration tests
- [ ] Write model tests
- [ ] Write schema tests
- [ ] Write service tests
- [ ] Write API integration tests
- [ ] Perform load testing
- [ ] Test user isolation
- [ ] Test villa availability updates

### Phase 7: Documentation
- [ ] Update API documentation
- [ ] Update database schema documentation
- [ ] Create migration guide for API consumers
- [ ] Document breaking changes
- [ ] Update user guides

### Phase 8: Deployment
- [ ] Deploy to staging
- [ ] Perform QA testing
- [ ] Fix any issues found
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Provide support for API consumers

---

## Appendix A: SQL DDL Examples

### Create booking_items Table
```sql
CREATE TABLE booking_items (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    booking_id INTEGER NOT NULL,
    package_id INTEGER NOT NULL,
    pax INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(15, 2) NOT NULL,
    discount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    line_total DECIMAL(15, 2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE,
    INDEX idx_booking_items_booking_id (booking_id),
    INDEX idx_booking_items_package_id (package_id),
    CONSTRAINT check_pax_positive CHECK (pax >= 1),
    CONSTRAINT check_unit_price_non_negative CHECK (unit_price >= 0),
    CONSTRAINT check_discount_non_negative CHECK (discount >= 0)
);
```

### Create booking_history Table
```sql
CREATE TABLE booking_history (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    booking_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_booking_history_booking_id (booking_id),
    INDEX idx_booking_history_user_id (user_id),
    INDEX idx_booking_history_created_at (created_at),
    CONSTRAINT check_change_type CHECK (
        change_type IN ('created', 'status_change', 'field_update', 'item_added',
                       'item_removed', 'villa_added', 'villa_removed', 'payment_received')
    )
);
```

---

## Appendix B: Example API Requests

### Create Booking (New Format)
```json
POST /api/bookings
{
    "customer_id": 123,
    "check_in": "2025-12-01",
    "check_out": "2025-12-05",
    "total_pax": 4,
    "notes": "Anniversary celebration",
    "sales_person_id": 5,
    "villas": [
        {
            "villa_id": 10
        }
    ],
    "items": [
        {
            "package_id": 15,
            "pax": 4,
            "unit_price": 1500000,
            "discount": 0,
            "line_total": 6000000
        },
        {
            "package_id": 20,
            "pax": 2,
            "unit_price": 500000,
            "discount": 50000,
            "line_total": 950000
        }
    ]
}
```

### Update Booking Items
```json
PATCH /api/bookings/123
{
    "items": [
        {
            "package_id": 15,
            "pax": 4,
            "unit_price": 1500000,
            "discount": 100000,
            "line_total": 5900000
        }
    ]
}
```

### Get Booking with History
```json
GET /api/bookings/123?include_history=true

Response:
{
    "id": 123,
    "booking_code": "BK-2025-001",
    "customer": {...},
    "check_in": "2025-12-01",
    "check_out": "2025-12-05",
    "status": "confirmed",
    "total": 6950000,
    "tax_total": 0,
    "amount_paid": 3000000,
    "amount_due": 3950000,
    "items": [...],
    "villas": [...],
    "history": [
        {
            "id": 1,
            "field_name": "status",
            "old_value": null,
            "new_value": "pending",
            "change_type": "created",
            "created_at": "2025-11-01T10:00:00"
        },
        {
            "id": 2,
            "field_name": "status",
            "old_value": "pending",
            "new_value": "confirmed",
            "change_type": "status_change",
            "created_at": "2025-11-02T14:30:00"
        }
    ]
}
```

---

## Appendix C: Status Transition Diagram

```
Booking Status Workflow:

    [pending] ──────────────────────────────────┐
        │                                        │
        │ confirm                                │ cancel
        ↓                                        ↓
    [confirmed] ────────────────────────────> [cancelled]
        │                                        
        │ check in                              
        ↓                                        
    [checked_in]                                
        │                                        
        │ check out                              
        ↓                                        
    [checked_out]                               
        │                                        
        │ complete (after payment)               
        ↓                                        
    [completed]                                 
```

**Valid Transitions:**
- `pending` → `confirmed`, `cancelled`
- `confirmed` → `checked_in`, `cancelled`
- `checked_in` → `checked_out`, `cancelled` (with penalty)
- `checked_out` → `completed`
- `cancelled` → (terminal state)
- `completed` → (terminal state)

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-03 | System Architect | Initial design specification |

**Approval:**

- [ ] Technical Lead
- [ ] Database Administrator
- [ ] Product Owner
- [ ] QA Lead

**Next Review Date:** After Phase 1 completion

---

*End of Document*