# Villa Availability Analysis

**Document Version:** 1.0  
**Date:** 2026-01-27  
**Author:** Code Analysis  

---

## Executive Summary

This document analyzes the current structure of the `villa_availability` table and its relationships with bookings, invoices, and quotations in the XerpeX ERP system. The analysis reveals that **only bookings actively manage villa availability**, while invoices and quotes merely reference villas without blocking dates.

---

## 1. VillaAvailability Model Structure

### 1.1 Database Schema

**Location:** [`app/models/villa.py`](app/models/villa.py:32-51)

```python
class VillaAvailability(Base):
    """Villa availability model"""
    __tablename__ = "villa_availability"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    
    # Availability Data
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=True)
    blocked_reason = Column(Text)
    
    # Audit Fields
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 1.2 Key Fields

| Field | Type | Nullable | Purpose |
|-------|------|----------|---------|
| `id` | Integer | No | Primary key |
| `villa_id` | Integer | No | References `villas.id` with CASCADE delete |
| `date` | Date | No | Specific date for availability check |
| `is_available` | Boolean | No | `True` = available, `False` = blocked |
| `blocked_reason` | Text | Yes | Human-readable reason for blocking (e.g., "Booked (Booking Code: BK-20260127-001)") |
| `updated_by` | Integer | Yes | References `users.id`, tracks who made the change |
| `updated_at` | DateTime | No | Timestamp of last update |

### 1.3 Relationships

- **Villa:** Many-to-one relationship with `Villa` model via `villa` property
- **User:** Many-to-one relationship with `User` model via `updated_by_user` property (tracks who modified availability)

### 1.4 Constraints

- No unique constraints on `(villa_id, date)` - allows multiple records per villa/date (potential issue)
- Date-based availability tracking (one record per villa per date)
- Cascade delete when villa is deleted

---

## 2. Current Availability Management

### 2.1 Booking Service Implementation

**Location:** [`app/services/booking.py`](app/services/booking.py:1383-1488)

#### 2.1.1 Availability Checking

**Function:** `check_villa_availability()` (Lines 1383-1433)

**Logic:**
- Checks each date from `check_in` to **one day before** `check_out` (exclusive checkout)
- Queries `villa_availability` for dates where `is_available = False`
- Supports `exclude_booking_id` parameter to exclude current booking when updating
- Returns tuple: `(is_available: bool, unavailable_dates: List[date])`

**Key Implementation Details:**
```python
# Date range: check_in to (check_out - 1 day)
while current_date < check_out:
    availability = db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id,
        VillaAvailability.date == current_date,
        VillaAvailability.is_available == False
    ).first()
    
    if availability:
        # Check if blocked by the booking being edited
        if exclude_booking_id and booking_code in availability.blocked_reason:
            continue  # Skip, this is the same booking
        unavailable_dates.append(current_date)
    
    current_date += timedelta(days=1)
```

#### 2.1.2 Availability Updates

**Function:** `update_villa_availability()` (Lines 1436-1488)

**Purpose:** Block or unblock villa dates when bookings are created, updated, or deleted

**Logic:**
- Iterates through date range (check_in to check_out - 1)
- For each date, either creates new or updates existing `VillaAvailability` record
- Sets `is_available` flag and updates `blocked_reason` with booking code
- Tracks `updated_by` user and `updated_at` timestamp

**Called By:**
1. **`create_booking()`** (Line 320-324): Blocks dates when booking created
2. **`add_booking_villa()`** (Line 994-997): Blocks dates when villa added to booking
3. **`remove_booking_villa()`** (Line 1136-1139): Unblocks dates when villa removed
4. **`delete_booking()`** (Line 616-621): Unblocks dates when booking deleted
5. **`convert_invoice_to_booking()`** (Line 1385-1388): Blocks dates when invoice converted to booking

### 2.2 Booking Lifecycle and Availability

| Booking Action | Availability Impact |
|----------------|---------------------|
| Create booking | ✅ Blocks villa dates (check_in to check_out-1) |
| Update booking dates | ✅ Re-checks availability for new dates |
| Add villa to booking | ✅ Blocks villa dates |
| Remove villa from booking | ✅ Unblocks villa dates |
| Delete booking | ✅ Unblocks villa dates |
| Convert invoice to booking | ✅ Blocks villa dates |

---

## 3. Invoice Relationship to Availability

### 3.1 Invoice-Villa Relationship

**Model:** [`app/models/payment.py`](app/models/payment.py:154-172)

```python
class InvoiceVilla(Base):
    """Invoice villa model - simple junction table"""
    __tablename__ = "invoice_villas"
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"))
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"))
```

**Purpose:** Simple many-to-many junction table linking invoices to villas

### 3.2 Invoice Service Behavior

**Location:** [`app/services/payment.py`](app/services/payment.py:170-297)

**Key Findings:**

#### ❌ **Invoices DO NOT Manage Availability**

1. **`create_invoice()`** (Lines 170-297):
   - Validates villas exist (Lines 193-199)
   - Creates `InvoiceVilla` records (Lines 268-273)
   - **Does NOT call `update_villa_availability()`**
   - **Does NOT block villa dates**

2. **`update_invoice()`** (Lines 300-453):
   - Can update villa associations (Lines 358-441)
   - **Does NOT check or update availability**

3. **Villa Calculation:**
   - Uses `villa.base_price` directly (Line 266)
   - **No nights calculation** (unlike bookings)
   - No date-based pricing

### 3.3 Invoice to Booking Conversion

**Function:** `convert_invoice_to_booking()` (Lines 1264-1439)

**Key Behavior:**
- **Checks availability** before conversion (Lines 1323-1336)
- **Blocks dates** when creating booking (Lines 1385-1388)
- Validates invoice status must be `partially_paid` or `paid`

**This is the ONLY point where invoices interact with villa availability**

---

## 4. Quote Relationship to Availability

### 4.1 Quote-Villa Relationship

**Model:** [`app/models/quote.py`](app/models/quote.py:73-91)

```python
class QuoteVilla(Base):
    """Quote villa model - simple junction table"""
    __tablename__ = "quote_villas"
    
    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"))
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"))
```

**Purpose:** Simple many-to-many junction table linking quotes to villas

### 4.2 Quote Service Behavior

**Location:** [`app/services/quote.py`](app/services/quote.py:128-264)

**Key Findings:**

#### ❌ **Quotes DO NOT Manage Availability**

1. **`create_quote()`** (Lines 128-264):
   - Validates villas exist (Lines 161-166)
   - Creates `QuoteVilla` records (Lines 228-239)
   - **Does NOT check availability**
   - **Does NOT block villa dates**

2. **`update_quote()`** (Lines 267-440):
   - Can update villa associations (Lines 327-414)
   - **Does NOT check or update availability**

3. **Villa Calculation:**
   - Uses `villa.base_price` (Line 232)
   - Comment states: "For quotes, just use base price without nights calculation"

### 4.3 Quote to Invoice Conversion

**Function:** `convert_quote_to_invoice()` (Lines 1139-1260)

**Key Behavior:**
- Simply copies `QuoteVilla` to `InvoiceVilla` (Lines 1234-1240)
- **Does NOT check availability**
- **Does NOT block dates**

---

## 5. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Villa Availability System                    │
└─────────────────────────────────────────────────────────────────┘

        ┌─────────┐           ┌──────────┐           ┌─────────┐
        │  Quote  │──────────▶│ Invoice  │──────────▶│ Booking │
        └─────────┘           └──────────┘           └─────────┘
             │                     │                       │
             │                     │                       │
             ▼                     ▼                       ▼
    quote_villas           invoice_villas           booking_villas
             │                     │                       │
             │                     │                       │
             ▼                     ▼                       ▼
        ┌─────────────────────────────────────────────────────────┐
        │                      villas                              │
        └─────────────────────────────────────────────────────────┘
                                                            │
                                                            │
                                                            ▼
                                             ┌──────────────────────────┐
                                             │  villa_availability      │
                                             │                          │
                                             │  ✅ Created/Updated by:  │
                                             │    - create_booking()    │
                                             │    - add_booking_villa() │
                                             │    - invoice→booking     │
                                             │                          │
                                             │  ❌ NOT touched by:      │
                                             │    - Quotes              │
                                             │    - Invoices            │
                                             └──────────────────────────┘

Legend:
  ──────▶  Conversion/Copy relationship
  ───────  Association relationship
  ✅      Active availability management
  ❌      No availability management
```

---

## 6. Current Gaps and Issues

### 6.1 Critical Gaps

#### 1. **No Availability Tracking for Quotes and Invoices**

**Impact:** Severe
- Quotes can be created for villas that are already booked
- Invoices can be issued for unavailable dates
- No warning to sales staff about conflicts
- Customer expectations vs reality mismatch

**Example Scenario:**
```
1. Booking created: Villa A for Jan 15-20 (dates blocked ✅)
2. Quote created: Villa A for Jan 17-22 (no check ❌)
3. Quote accepted and converted to invoice (no check ❌)
4. Invoice to booking conversion: FAILS - villa unavailable ❌
```

#### 2. **Inconsistent Date Range Logic**

**Quotes and Invoices:**
- Have `check_in` and `check_out` fields
- Fields are **NULLABLE** (can be None)
- Used for display only, not availability logic

**Bookings:**
- Have `check_in` and `check_out` fields  
- Fields are **REQUIRED** (NOT NULL)
- Actually block dates in `villa_availability`

#### 3. **No Unique Constraint on (villa_id, date)**

**Current Schema:**
```python
# villa_availability table
# No unique constraint on (villa_id, date)
```

**Issue:**
- Multiple records can exist for same villa on same date
- Potential for data inconsistency
- Queries must search all records for a date

#### 4. **Blocked Reason String Parsing**

**Current Implementation:**
```python
if booking and f"Booking Code: {booking.booking_code}" in availability.blocked_reason:
    # This is same booking, skip
    continue
```

**Issues:**
- Brittle string-based logic
- No formal relationship to booking
- Cannot query "which booking blocked this date?" efficiently
- Manual string formatting risk

### 6.2 Business Logic Gaps

#### 1. **No Soft Holds/Reservations**

- Quotes don't reserve villas even temporarily
- No "pending confirmation" state for availability
- Risk of double-booking between quote and acceptance

#### 2. **No Availability Preview in Quotes**

- Quote creation doesn't show if villas are available
- Sales staff must manually check bookings
- No automated availability suggestions

#### 3. **Status Transition Issues**

**Current Flow:**
```
Quote (no availability check)
  ↓
Invoice (no availability check)
  ↓
Booking (checks availability - may fail!)
```

**Should Be:**
```
Quote (checks availability, shows warning)
  ↓
Invoice (re-checks availability, confirms dates)
  ↓
Booking (guaranteed available, blocks dates)
```

### 6.3 Data Integrity Gaps

#### 1. **Orphaned Availability Records**

- If booking deleted but availability update fails, dates stay blocked
- No cleanup mechanism for stale availability records
- No validation that blocked_reason references valid booking

#### 2. **No Audit Trail for Availability Changes**

- `updated_by` and `updated_at` track changes
- But no history of WHO changed availability, WHEN, and WHY
- Cannot reconstruct availability timeline

#### 3. **Missing Constraints**

```sql
-- Missing constraints:
-- 1. UNIQUE (villa_id, date)
-- 2. CHECK (blocked_reason IS NOT NULL WHEN is_available = FALSE)
-- 3. CHECK (updated_by IS NOT NULL WHEN is_available = FALSE)
```

---

## 7. Required Updates

### 7.1 High Priority (Critical)

#### 1. Add Availability Checking to Quote Creation
**Location:** [`app/services/quote.py:create_quote()`](app/services/quote.py:128-264)

**Required Changes:**
```python
# After validating villas exist (around line 166)
if quote.check_in and quote.check_out:
    for villa_id in quote.villas:
        is_available, unavailable_dates = check_villa_availability(
            db, villa_id, quote.check_in, quote.check_out
        )
        if not is_available:
            # Log warning or raise exception
            logger.warning(
                f"Quote {quote_number}: Villa {villa_id} has conflicts on {unavailable_dates}"
            )
            # Option 1: Raise error
            # Option 2: Add warning to quote notes
            # Option 3: Mark quote with "availability_warning" flag
```

#### 2. Add Availability Checking to Invoice Creation
**Location:** [`app/services/payment.py:create_invoice()`](app/services/payment.py:170-297)

**Required Changes:**
```python
# After validating villas (around line 199)
if invoice.check_in and invoice.check_out:
    for villa_id in invoice.villas:
        is_available, unavailable_dates = check_villa_availability(
            db, villa_id, invoice.check_in, invoice.check_out
        )
        if not is_available:
            logger.warning(
                f"Invoice {invoice_number}: Villa {villa_id} conflicts on {unavailable_dates}"
            )
            # Business rule decision needed:
            # - Allow invoice creation with warning?
            # - Block invoice creation?
            # - Require override permission?
```

#### 3. Add Unique Constraint to villa_availability
**Location:** Database migration needed

**SQL:**
```sql
ALTER TABLE villa_availability 
ADD CONSTRAINT unique_villa_date UNIQUE (villa_id, date);
```

**Impact:**
- Prevents duplicate availability records
- Requires data cleanup before applying
- May need to handle constraint violations in code

### 7.2 Medium Priority (Important)

#### 4. Replace String-Based Booking Reference
**Proposal:** Add `booking_id` foreign key to `villa_availability`

**Schema Change:**
```python
class VillaAvailability(Base):
    # Add new field
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True)
    
    # Add relationship
    booking = relationship("Booking", back_populates="villa_availabilities")
```

**Benefits:**
- Direct relationship to blocking booking
- Cascading delete (availability freed when booking deleted)
- Efficient queries: "which booking blocked this date?"
- Can show booking details in availability UI

#### 5. Make check_in/check_out Required for Quotes/Invoices
**Impact:** Large

**Current:**
- `Quote.check_in` and `Quote.check_out` are nullable
- `Invoice.check_in` and `Invoice.check_out` are nullable

**Proposed:**
- Make fields required (NOT NULL)
- Add CHECK constraint: `check_out > check_in`
- Update existing records to have dates

**Requires:**
- Data migration for existing quotes/invoices
- Frontend validation updates
- API schema changes

#### 6. Add Availability History Table
**Purpose:** Track all availability changes for audit

**Schema:**
```python
class VillaAvailabilityHistory(Base):
    __tablename__ = "villa_availability_history"
    
    id = Column(Integer, primary_key=True)
    villa_id = Column(Integer, ForeignKey("villas.id"))
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, nullable=False)
    blocked_reason = Column(Text)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="SET NULL"))
    change_type = Column(String(20))  # 'blocked', 'unblocked', 'manual'
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(DateTime, default=datetime.utcnow)
```

### 7.3 Low Priority (Enhancement)

#### 7. Add Availability Soft Holds
**Purpose:** Temporarily reserve villas during quote/invoice process

**Schema Addition:**
```python
class VillaAvailability(Base):
    # Add fields
    hold_type = Column(String(20))  # 'hard_block', 'soft_hold', 'available'
    hold_expires_at = Column(DateTime, nullable=True)
    hold_by_quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True)
    hold_by_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
```

**Business Rules:**
- Soft holds expire after X hours
- Hard blocks (bookings) never expire
- Soft holds can be overridden by authorized users

#### 8. Add Availability Calendar View
**Features:**
- Show all bookings on calendar
- Color-code by booking status
- Filter by villa, date range, customer
- Click to see booking details

#### 9. Add Availability Suggestions
**Purpose:** Suggest available villas when requested ones are unavailable

**Algorithm:**
```python
def suggest_alternative_villas(
    requested_villa_id: int,
    check_in: date,
    check_out: date,
    db: Session
) -> List[Villa]:
    """Find villas with similar capacity/features that are available"""
    requested_villa = get_villa(db, requested_villa_id)
    
    available_villas = []
    for villa in db.query(Villa).filter(
        Villa.capacity == requested_villa.capacity,
        Villa.is_active == True,
        Villa.id != requested_villa_id
    ):
        is_available, _ = check_villa_availability(
            db, villa.id, check_in, check_out
        )
        if is_available:
            available_villas.append(villa)
    
    return available_villas
```

---

## 8. Implementation Recommendations

### 8.1 Phase 1: Critical Fixes (Week 1)

1. **Add unique constraint** on `(villa_id, date)`
2. **Add availability checks** to quote creation (warning only)
3. **Add availability checks** to invoice creation (warning only)
4. **Update documentation** with current behavior

**Deliverables:**
- Database migration script
- Updated service functions
- Integration tests
- User documentation

### 8.2 Phase 2: Structural Improvements (Week 2-3)

1. **Add booking_id** foreign key to `villa_availability`
2. **Make check_in/check_out required** for quotes/invoices
3. **Add availability history** table
4. **Update delete_booking** to use CASCADE instead of manual cleanup

**Deliverables:**
- Database migrations
- Updated models and services
- Data migration scripts for existing records
- Updated API endpoints

### 8.3 Phase 3: Feature Enhancements (Week 4+)

1. **Implement soft holds** for quotes/invoices
2. **Add availability calendar** UI
3. **Add alternative villa suggestions**
4. **Add conflict resolution** workflow

**Deliverables:**
- New API endpoints
- Frontend components
- Business logic for holds
- Admin tools for conflict resolution

### 8.4 Testing Requirements

#### Unit Tests Needed:

```python
# Test villa availability checking
def test_check_villa_availability_with_booking()
def test_check_villa_availability_exclude_current_booking()
def test_check_villa_availability_no_conflicts()

# Test availability updates
def test_update_villa_availability_create_new()
def test_update_villa_availability_update_existing()
def test_update_villa_availability_unblock()

# Test quote behavior
def test_quote_creation_checks_availability()
def test_quote_warns_on_unavailable_villas()

# Test invoice behavior
def test_invoice_creation_checks_availability()
def test_invoice_warns_on_unavailable_villas()

# Test booking to villa availability
def test_booking_blocks_availability_on_create()
def test_booking_unblocks_availability_on_delete()
def test_booking_date_change_updates_availability()
```

#### Integration Tests Needed:

```python
# Test full workflow
def test_quote_to_invoice_to_booking_availability_flow()
def test_concurrent_booking_creation_same_villa()
def test_availability_cascade_on_booking_delete()
def test_invoice_to_booking_conversion_unavailable_dates()
```

---

## 9. Risk Assessment

### 9.1 High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Double bookings due to quote/invoice not checking availability | **Critical** | Implement availability checks immediately (Phase 1) |
| Data inconsistency from multiple records per villa/date | **High** | Add unique constraint (Phase 1) |
| Failed invoice-to-booking conversions | **High** | Check availability in quote/invoice creation (Phase 1) |

### 9.2 Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Orphaned availability records | **Medium** | Add booking_id FK with CASCADE (Phase 2) |
| Cannot track availability history | **Medium** | Add availability history table (Phase 2) |
| Manual string parsing in blocked_reason | **Medium** | Replace with booking_id FK (Phase 2) |

### 9.3 Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| No soft hold mechanism | **Low** | Feature enhancement (Phase 3) |
| No alternative villa suggestions | **Low** | Feature enhancement (Phase 3) |

---

## 10. Conclusion

### Current State Summary

✅ **Working:**
- Booking service properly manages villa availability
- Availability checking works for booking date range
- Manual override supported via `exclude_booking_id`

❌ **Not Working:**
- Quotes do NOT check or manage availability
- Invoices do NOT check or manage availability
- Risk of creating quotes/invoices for unavailable dates
- No prevention of conflicts until booking creation

### Next Steps

1. **Immediate:** Implement availability checks in quote/invoice creation (warnings)
2. **Short-term:** Add unique constraint, add booking_id FK
3. **Medium-term:** Make dates required, add history tracking
4. **Long-term:** Implement soft holds and enhanced features

### Success Criteria

- ✅ Zero double-bookings on same villa/dates
- ✅ Sales staff see availability warnings when creating quotes
- ✅ All villas have accurate real-time availability status
- ✅ Audit trail exists for all availability changes
- ✅ Invoices successfully convert to bookings 100% of time (when dates available)

---

**Document Status:** Draft for Review  
**Next Review Date:** 2026-02-03  
**Owner:** Development Team
