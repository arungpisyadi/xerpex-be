# Invoice, Quote, and Booking Workflow Documentation

## Executive Summary

This document details how invoices and quotes relate to bookings and villa availability management in the XerpeX ERP System.

**Key Finding:** Invoices and quotes do NOT directly manage villa_availability. Only bookings manage villa_availability. However, invoices can be converted to bookings, at which point villa_availability is properly managed through the booking service.

## Workflow Overview

```
Quote (draft) → Quote (accepted) → Invoice → Booking (with villa_availability)
```

## 1. Quote → Invoice Conversion

### Service Function
- **Location:** [`app/services/payment.py`](app/services/payment.py:1139-1260)
- **Function:** [`convert_quote_to_invoice()`](app/services/payment.py:1139)

### Workflow
1. **Validation:**
   - Quote must have status `'accepted'` (line 1178-1182)
   - Quote cannot already be converted to an invoice (line 1185-1190)
   - Role-based access control applies (lines 1165-1167)

2. **Conversion Process:**
   - Generates unique invoice number (lines 1192-1195)
   - Creates invoice with `draft` status (line 1208)
   - Copies all quote items to invoice items (lines 1221-1232)
   - Copies all quote villas to invoice villas (lines 1234-1240)
   - Preserves check_in/check_out dates if present (lines 1206-1207)
   - Sets tax_total to 0.00 (line 1212)
   - Initializes amount_paid to 0.00 and amount_due to quote.total (lines 1210-1211)

3. **Villa Availability:**
   - **No villa_availability changes** - Invoices do not block villas
   - Villa relationships are stored in `invoice_villas` table for reference only

4. **History Logging:**
   - Records conversion event in invoice history (lines 1245-1258)
   - Event type: `"invoice_converted_from_quote"`
   - Category: `"lifecycle"`

### Data Flow
```
Quote Fields → Invoice Fields:
- user_id → user_id
- sales_person_id → sales_person_id
- customer_id → customer_id
- quote.id → invoice.quote_id (reference)
- total → total
- check_in → check_in (optional)
- check_out → check_out (optional)
- items[] → items[] (full copy)
- villas[] → villas[] (reference only)
```

### Access Control
- Admin, Finance, Sales: Can convert any user's accepted quotes
- Regular users: Can only convert their own accepted quotes

## 2. Invoice → Booking Conversion

### Service Function
- **Location:** [`app/services/payment.py`](app/services/payment.py:1264-1438)
- **Function:** [`convert_invoice_to_booking()`](app/services/payment.py:1264)

### Workflow
1. **Validation:**
   - Invoice must have status `'partially_paid'` or `'paid'` (lines 1299-1303)
   - Invoice cannot already be converted to a booking (lines 1306-1313)
   - check_out must be after check_in (lines 1316-1320)
   - Role-based access control applies (lines 1290-1296)

2. **Villa Availability Check (CRITICAL):**
   ```python
   # Lines 1322-1334
   for invoice_villa in invoice.villas:
       is_available, unavailable_dates = check_villa_availability(
           db, invoice_villa.villa_id, request_data.check_in, request_data.check_out
       )
       
       if not is_available:
           raise HTTPException(status_code=400, detail=f"{villa_name} is not available")
   ```
   - **This is where villa_availability is first checked**
   - Conversion will FAIL if any villa is unavailable for requested dates

3. **Conversion Process:**
   - Generates unique booking code (lines 1337-1339)
   - Creates booking with `'pending'` status (lines 1342-1358)
   - **Transfers payment information:** (lines 1354-1355)
     - `amount_paid` = invoice.amount_paid
     - `amount_due` = invoice.amount_due
   - Copies all invoice items to booking items (lines 1363-1374)
   - Copies all invoice villas to booking villas (lines 1376-1388)

4. **Villa Availability Management (CRITICAL):**
   ```python
   # Lines 1384-1388
   update_villa_availability(
       db, invoice_villa.villa_id, request_data.check_in, request_data.check_out,
       booking_code, current_user.id, is_available=False
   )
   ```
   - **THIS IS WHERE VILLAS ARE BLOCKED**
   - Creates `VillaAvailability` records for each day in the date range (check_in to check_out, excluding check_out)
   - Marks villas as unavailable (`is_available=False`)
   - Records booking_code as the blocked_reason
   - Delegates to [`app/services/booking.update_villa_availability()`](app/services/booking.py)

5. **History Logging:**
   - Invoice history: Event type `"invoice_converted_to_booking"` (lines 1393-1407)
   - Booking history: Two events recorded (lines 1409-1431)
     - `conversion_source="invoice"`
     - `source_invoice="Invoice #{number}"`

### Data Flow
```
Invoice Fields + Request Data → Booking Fields:
- invoice.user_id → booking.user_id
- invoice.customer_id → booking.customer_id
- invoice.sales_person_id → booking.sales_person_id
- request_data.check_in → booking.check_in
- request_data.check_out → booking.check_out
- request_data.total_pax → booking.total_pax
- request_data.notes → booking.notes
- invoice.total → booking.total
- invoice.tax_total → booking.tax_total
- invoice.amount_paid → booking.amount_paid (TRANSFERRED)
- invoice.amount_due → booking.amount_due (TRANSFERRED)
- status: Always set to 'pending'
- items[] → items[] (full copy)
- villas[] → villas[] + VillaAvailability records
```

### Access Control
- Admin, Finance, Sales: Can convert any user's invoices
- Regular users: Can only convert their own invoices

## 3. Villa Availability Management

### Key Points
1. **Quotes:** No villa_availability impact
2. **Invoices:** No villa_availability impact (villas stored as reference only)
3. **Bookings:** Full villa_availability management

### When Villa Availability is Updated
- **Only during invoice-to-booking conversion** (lines 1384-1388 in payment.py)
- Uses booking service's [`update_villa_availability()`](app/services/booking.py) function
- Creates individual `VillaAvailability` records for each date in range

### Villa Availability Records
```python
VillaAvailability(
    villa_id=villa_id,
    date=specific_date,  # For each day from check_in to check_out (exclusive)
    is_available=False,
    blocked_reason=f"Booked: {booking_code}",
    updated_by=user_id,
    updated_at=datetime.utcnow()
)
```

### Availability Check Before Conversion
The [`check_villa_availability()`](app/services/booking.py) function (called at line 1324):
- Queries `VillaAvailability` table for the date range
- Returns `(is_available: bool, unavailable_dates: List[date])`
- Conversion is blocked if any day is unavailable

## 4. Payment Tracking Across Conversions

### Quote Stage
- No payment tracking (quotes are proposals only)

### Invoice Stage
- Fields: `amount_paid`, `amount_due`, `total`
- Payments can be added via [`create_payment()`](app/services/payment.py:784)
- Status automatically updates based on payments:
  - `draft` → `sent` → `partially_paid` → `paid`
  - Or `sent` → `overdue` if past due_date

### Booking Stage
- **Payment amounts are transferred from invoice** (lines 1354-1355)
- Booking inherits the payment state from invoice
- Allows tracking of deposits paid at invoice stage

## 5. Status Requirements and Transitions

### Quote Status Flow
```
draft → sent → accepted ──→ Can convert to invoice
              ↓
          declined → Can reopen to draft
              ↓
          expired → Can reopen to draft
```

### Invoice Status Flow
```
draft → sent → partially_paid ──→ Can convert to booking
              ↓
          overdue    paid ──────→ Can convert to booking
              ↓
          cancelled
```

**ONLY** `partially_paid` or `paid` invoices can be converted to bookings.

### Booking Status
- All converted bookings start with status: `'pending'`
- Further status management handled by booking service

## 6. Duplicate Prevention

### Quote → Invoice
- Check: Does `Invoice.quote_id` already exist for this quote? (line 1185)
- Prevention: Raise HTTPException if already converted

### Invoice → Booking  
- Check: Does `Invoice.booking_id` exist? (lines 1306-1308)
- Note: The code checks using a join query, but `invoice.booking_id` field tracks this relationship
- Prevention: Raise HTTPException if already converted

## 7. History and Audit Trail

### Quote History
- Event: Quote created, updated, status changed, deleted
- Not related to villa_availability

### Invoice History
- Event type: `"invoice_converted_from_quote"` (line 1250)
- Event type: `"invoice_converted_to_booking"` (line 1398)
- Category: `"lifecycle"`
- Metadata includes: booking_id, booking_code, total_amount, customer_name

### Booking History
- Two events created during conversion:
  1. `conversion_source="invoice"` (field tracking)
  2. `source_invoice="Invoice #XXX"` (reference tracking)
- These events document the origin of the booking

## 8. Test Coverage

Comprehensive test suites exist for both conversions:

### Quote → Invoice Tests
- **File:** [`app/tests/test_quote_convert_access_control.py`](app/tests/test_quote_convert_access_control.py)
- Tests: Role-based access, accepted status requirement, duplicate prevention, data copying

### Invoice → Booking Tests
- **File:** [`app/tests/test_invoice_to_booking_conversion.py`](app/tests/test_invoice_to_booking_conversion.py)
- Tests: Status validation, villa availability checks, duplicate prevention, data mapping, history recording
- **Critical Test:** `test_conversion_records_villa_availability()` (line 880)
  - Verifies villa_availability records are created
  - Confirms records are marked unavailable
  - Validates booking_code is in blocked_reason

## 9. API Endpoints

### Convert Quote to Invoice
- **Endpoint:** `POST /quotes/{quote_id}/convert-to-invoice`
- **Controller:** [`app/controllers/quote.py:377`](app/controllers/quote.py:377)
- **Schema:** [`QuoteToInvoiceRequest`](app/schemas/payment.py) with issue_date, due_date, notes

### Convert Invoice to Booking
- **Endpoint:** `POST /invoices/{invoice_id}/convert-to-booking`
- **Controller:** [`app/controllers/invoice.py:181`](app/controllers/invoice.py:181)
- **Schema:** [`InvoiceToBookingRequest`](app/schemas/payment.py) with check_in, check_out, total_pax, notes

## 10. Recommendations

### Current Implementation: ✅ CORRECT

The current implementation is **architecturally sound**:

1. **Separation of Concerns:**
   - Quotes are proposals (no villa blocking)
   - Invoices are financial documents (no villa blocking)
   - Bookings are reservations (villa blocking)
   - ✅ This is the correct design

2. **Villa Availability Management:**
   - Only bookings manage villa_availability
   - Conversion from invoice to booking properly checks and updates availability
   - ✅ No changes needed

3. **Payment Tracking:**
   - Amount paid/due correctly transferred from invoice to booking
   - ✅ Maintains financial continuity

4. **Access Control:**
   - Role-based permissions properly enforced
   - ✅ Admin/Finance/Sales can manage all, regular users limited to own records

### No Changes Required

**The invoice and quote services do NOT need any updates for villa_availability management.** The current workflow is correct:

1. Quote stage: No villa blocking (proposals can include unavailable villas)
2. Invoice stage: No villa blocking (invoices can be created for future dates)
3. Booking stage: Villa availability checked and blocked (actual reservations)

This design allows flexibility in the sales process while ensuring villa availability is only managed when actual bookings are confirmed.

## 11. Summary

| Stage | Villa Availability | Payment Tracking | Status Requirements |
|-------|-------------------|------------------|---------------------|
| **Quote** | ❌ No impact | ❌ No payment | Must be `accepted` to convert |
| **Invoice** | ❌ No impact (reference only) | ✅ Tracks payments | Must be `partially_paid` or `paid` to convert |
| **Booking** | ✅ Fully managed | ✅ Inherits from invoice | Starts as `pending` |

### Conversion Flow
```
Quote (accepted) 
    ↓ convert_quote_to_invoice()
    ↓ • Copies items/villas
    ↓ • No villa blocking
    ↓
Invoice (partially_paid/paid)
    ↓ convert_invoice_to_booking()
    ↓ • Checks villa availability
    ↓ • Transfers payment amounts
    ↓ • Copies items/villas
    ↓ • BLOCKS VILLAS via update_villa_availability()
    ↓
Booking (pending)
    • Villa availability managed
    • Payment tracking continues
    • Full booking lifecycle
```

### Villa Availability Management Location
- **Service:** [`app/services/booking.py`](app/services/booking.py)
- **Function:** [`update_villa_availability()`](app/services/booking.py)
- **Called By:** [`convert_invoice_to_booking()`](app/services/payment.py:1385) at line 1385
- **Effect:** Creates `VillaAvailability` records with `is_available=False`

---

**Document Status:** Complete  
**Last Updated:** 2026-01-27  
**Verification:** All code references confirmed against source files
