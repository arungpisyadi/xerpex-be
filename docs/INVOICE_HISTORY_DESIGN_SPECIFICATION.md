# Invoice History Functionality Design Specification

## Executive Summary

This document specifies the design for implementing invoice history functionality in the XerpeX ERP system. The feature will provide a comprehensive audit trail of invoice lifecycle events, focusing on high-level workflow actions for customer service and business reporting needs.

## Current System Analysis

### Existing Invoice Structure
- **Models**: [`Invoice`](app/models/payment.py:35), [`InvoiceItem`](app/models/payment.py:76), [`Payment`](app/models/payment.py:11)
- **Controllers**: [`InvoiceController`](app/controllers/invoice.py:23) with 15+ endpoints
- **Services**: [`PaymentService`](app/services/payment.py:28) handling invoice CRUD and workflow
- **Schemas**: [`InvoiceResponse`](app/schemas/payment.py:124), [`PaymentResponse`](app/schemas/payment.py:173)

### Current Capabilities
- Invoice status management (draft, sent, paid, overdue, cancelled)
- Payment tracking and status updates
- Quote-to-invoice conversion
- Workflow actions (send, mark-paid, cancel, reopen)
- User isolation based on roles

### Missing Functionality
- **No audit trail** of who made changes and when
- **No history tracking** of invoice lifecycle events
- **No customer service visibility** into invoice interactions
- Missing route: [`/api/v1/invoices/{invoice_id}/history`](app/controllers/invoice.py:433)

## Requirements & Scope

### Primary Use Cases
1. **Customer Service**: Track invoice interactions for support inquiries
2. **Business Reporting**: Analyze invoice workflow patterns
3. **User Accountability**: Audit trail of who performed actions

### Event Tracking Scope
**High-level events only** (not field-level changes):
- Invoice lifecycle events
- Status changes and workflow actions
- Payment events
- System-generated events

## Database Design

### New Table: `invoice_history`

```sql
CREATE TABLE invoice_history (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT check_event_category CHECK (
        event_category IN ('lifecycle', 'status', 'workflow', 'payment')
    )
);

-- Performance Indexes
CREATE INDEX idx_invoice_history_invoice_id ON invoice_history(invoice_id);
CREATE INDEX idx_invoice_history_created_at_desc ON invoice_history(created_at DESC);
CREATE INDEX idx_invoice_history_event_category ON invoice_history(event_category);
CREATE INDEX idx_invoice_history_composite ON invoice_history(invoice_id, created_at DESC, event_category);
```

### Event Types & Categories

#### Lifecycle Events
- `invoice_created`: New invoice created from scratch
- `invoice_converted_from_quote`: Invoice created from accepted quote
- `invoice_modified`: Invoice data updated (non-status changes)
- `invoice_deleted`: Draft invoice deleted

#### Status Changes
- `status_changed`: Manual status updates via API
- `marked_overdue`: System automatically marked as overdue

#### Workflow Actions
- `invoice_sent`: Status changed from draft to sent
- `invoice_cancelled`: Invoice cancelled by user
- `invoice_reopened`: Cancelled invoice reopened to draft

#### Payment Events
- `payment_added`: New payment record created
- `payment_completed`: Payment status changed to completed
- `payment_failed`: Payment status changed to failed
- `fully_paid`: Invoice marked as fully paid

## API Specification

### Endpoint: `GET /api/v1/invoices/{invoice_id}/history`

#### Request Parameters
```typescript
interface HistoryQueryParams {
  skip?: number;          // Default: 0
  limit?: number;         // Default: 50, Max: 100
  event_category?: 'lifecycle' | 'status' | 'workflow' | 'payment';
  from_date?: string;     // ISO date format
  to_date?: string;       // ISO date format
}
```

#### Response Schema
```json
{
  "invoice_id": 123,
  "invoice_number": "INV-2024-001",
  "history": [
    {
      "id": 1,
      "event_type": "invoice_created",
      "event_category": "lifecycle",
      "description": "Invoice created",
      "user_name": "John Doe",
      "user_email": "john@company.com",
      "metadata": {
        "total_amount": "1500.00",
        "customer_name": "ABC Corp",
        "status": "draft"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "formatted_date": "January 15, 2024 at 10:30 AM"
    }
  ],
  "total_events": 15,
  "skip": 0,
  "limit": 50
}
```

#### Error Responses
- `404 Not Found`: Invoice not found or access denied
- `400 Bad Request`: Invalid query parameters
- `403 Forbidden`: User lacks permission to view invoice

## Implementation Strategy

### Phase 1: Foundation (Week 1)
1. **Database Migration**: Create `invoice_history` table
2. **Models**: Add `InvoiceHistory` SQLAlchemy model
3. **Schemas**: Create Pydantic schemas for API responses
4. **Service Layer**: Implement history logging service
5. **Controller**: Add history endpoint to invoice controller

### Phase 2: Event Integration (Week 2-3)
**Integrate history logging into existing service functions:**

```python
# Example integration in app/services/payment.py
def create_invoice(db: Session, invoice: InvoiceCreate, current_user: User) -> Invoice:
    # ... existing code ...
    
    # Log history event
    log_invoice_history(
        db=db,
        invoice_id=db_invoice.id,
        user_id=current_user.id,
        event_type="invoice_created",
        event_category="lifecycle",
        description="Invoice created",
        metadata={
            "total_amount": str(db_invoice.total),
            "customer_name": customer.name,
            "status": db_invoice.status
        }
    )
    
    return db_invoice
```

**Functions to modify:**
- [`create_invoice()`](app/services/payment.py:147)
- [`update_invoice_status()`](app/services/payment.py:323)
- [`convert_quote_to_invoice()`](app/services/payment.py:697)
- [`create_payment()`](app/services/payment.py:504)
- [`update_payment_status()`](app/services/payment.py:612)

### Phase 3: Historical Data Migration (Week 4)
**Migration script for existing data:**
```python
def migrate_existing_invoice_history(db: Session):
    """Create basic history for existing invoices"""
    invoices = db.query(Invoice).all()
    
    for invoice in invoices:
        # Create invoice_created event
        log_invoice_history(
            db=db,
            invoice_id=invoice.id,
            user_id=invoice.user_id,
            event_type="invoice_created",
            description="Invoice created (migrated)",
            metadata={"migrated": True}
        )
        
        # Create payment events from existing payments
        for payment in invoice.payments:
            log_invoice_history(
                db=db,
                invoice_id=invoice.id,
                user_id=payment.user_id,
                event_type="payment_added",
                description=f"Payment of ${payment.amount} added (migrated)"
            )
```

## File Structure

### New Files to Create
```
app/models/history.py              # InvoiceHistory model
app/schemas/history.py             # History response schemas  
app/services/history.py            # History logging functions
migrations/versions/XXX_add_invoice_history.py  # Database migration
```

### Files to Modify
```
app/controllers/invoice.py         # Add history endpoint
app/services/payment.py            # Add history logging calls
app/schemas/payment.py             # Import history schemas if needed
```

## Performance Considerations

### Query Optimization
- **Primary Index**: `invoice_id` for fast lookups
- **Temporal Index**: `created_at DESC` for chronological ordering
- **Composite Index**: `(invoice_id, created_at DESC, event_category)` for filtered queries
- **Pagination**: Always use `LIMIT`/`OFFSET` with reasonable defaults

### Scalability Metrics
- **Expected Growth**: ~12,000 records/year for 100 invoices/month
- **Query Performance Target**: < 200ms for history endpoint
- **Memory Usage**: ~25KB per 50-event response

### Caching Strategy
- **Redis Cache**: 1-hour TTL for frequently accessed invoice histories
- **Cache Key**: `invoice_history:{invoice_id}:{skip}:{limit}:{category?}`
- **Cache Invalidation**: On new history events for that invoice

### Data Retention
```sql
-- Archive strategy for large datasets
CREATE TABLE invoice_history_archive AS 
SELECT * FROM invoice_history 
WHERE created_at < NOW() - INTERVAL '2 years';
```

## Security & Access Control

### User Isolation
- Apply same role-based filtering as existing invoice system
- Users can only see history for invoices they have access to
- History endpoint respects [`get_user_filter_condition()`](app/utils/security.py) logic

### Data Privacy
- Store minimal user information (ID, not sensitive data)
- Metadata should not contain customer sensitive information
- Log events, not detailed field changes

## Error Handling

### History Logging Failures
```python
def safe_log_history(db: Session, **kwargs):
    """Log history event with error handling"""
    try:
        log_invoice_history(db=db, **kwargs)
    except Exception as e:
        # Log error but don't break main operation
        logger.error(f"Failed to log invoice history: {e}")
```

### Principles
- **Non-blocking**: History logging failures must not break main operations
- **Graceful Degradation**: System continues working without history
- **Error Monitoring**: Log history failures for investigation

## Testing Strategy

### Unit Tests
- History model creation and validation
- History service functions
- Event logging integration
- Query filtering and pagination

### Integration Tests
- Complete invoice workflow with history tracking
- API endpoint responses and error cases
- Database migrations and rollbacks
- Performance testing with large datasets

### Test Data Scenarios
```python
# Example test case
def test_invoice_lifecycle_history():
    # Create invoice -> Check history event
    # Update status -> Check status change event  
    # Add payment -> Check payment event
    # Mark paid -> Check fully_paid event
    # Verify chronological order and metadata
```

## Monitoring & Maintenance

### Key Metrics
- History table growth rate
- Query performance trends
- History logging success/failure rates
- Cache hit rates for history endpoints

### Maintenance Tasks
- Monthly review of query performance
- Quarterly data retention policy execution
- Annual review of event types and categories

## Future Enhancements

### Phase 2 Features (Future)
- **Field-level change tracking** for detailed auditing
- **Bulk history export** for compliance reporting
- **History event webhooks** for real-time notifications
- **Customer portal history** showing customer-visible events only

### Integration Opportunities
- **Email notifications** on status changes
- **Dashboard widgets** showing recent invoice activity
- **Advanced analytics** on invoice processing patterns

---

## Implementation Checklist

- [ ] Create database migration for `invoice_history` table
- [ ] Implement `InvoiceHistory` model in [`app/models/history.py`](app/models/history.py)
- [ ] Create Pydantic schemas in [`app/schemas/history.py`](app/schemas/history.py)
- [ ] Implement history service in [`app/services/history.py`](app/services/history.py)
- [ ] Add history endpoint to [`app/controllers/invoice.py`](app/controllers/invoice.py)
- [ ] Integrate history logging into existing service functions
- [ ] Create migration script for existing invoice data
- [ ] Add unit and integration tests
- [ ] Update API documentation
- [ ] Deploy and monitor performance

---

**Document Version**: 1.0  
**Created**: January 2024  
**Last Updated**: January 2024  
**Status**: Ready for Implementation