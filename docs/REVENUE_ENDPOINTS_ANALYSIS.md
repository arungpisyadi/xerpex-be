# Revenue Endpoints Analysis for XerpeX ERP System

## Executive Summary

This document provides a comprehensive analysis of the existing codebase structure to guide the implementation of three new revenue-related endpoints:

1. **Monthly Revenue Endpoint** - Array of month 1-12 with revenue amounts
2. **Current Month Performance Endpoint** - Target, revenue, today's revenue, percentage
3. **Current Year Performance Endpoint** - Target, revenue, percentage

## 1. Invoice Model Structure & Revenue Data Storage

### Invoice Model Analysis (`app/models/payment.py`)

The [`Invoice`](app/models/payment.py:35) model stores revenue data in the following structure:

```python
class Invoice(Base):
    __tablename__ = "invoices"
    
    # Key revenue-related fields:
    total = Column(Numeric(10, 2), nullable=False, default=0.00)           # Total invoice amount
    amount_due = Column(Numeric(10, 2), nullable=False, default=0.00)      # Remaining amount due
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0.00)     # Amount paid so far
    status = Column(String(20), nullable=False, default="draft")           # Invoice status
    issue_date = Column(Date, nullable=False, default=date.today)          # Invoice issue date
    sales_person_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Sales person
```

### Key Revenue Calculation Insights

1. **Revenue Source**: Revenue is calculated from [`Invoice.total`](app/models/payment.py:49) field
2. **Revenue Recognition**: Based on existing target service patterns, revenue appears to be recognized when invoice status is `'paid'`
3. **Date Field for Aggregation**: Use [`Invoice.issue_date`](app/models/payment.py:45) for monthly/yearly grouping
4. **Sales Person Attribution**: Use [`Invoice.sales_person_id`](app/models/payment.py:41) for user-specific calculations

### Revenue Query Pattern from Target Service

From [`app/services/target.py`](app/services/target.py:38), line 38-45:
```python
# Sum total from paid invoices for the sales person in the given month/year
result = self.db.query(func.sum(Invoice.total)).filter(
    and_(
        Invoice.sales_person_id == user_id,
        Invoice.status == 'paid',
        extract('year', Invoice.issue_date) == year,
        extract('month', Invoice.issue_date) == month
    )
).scalar()
```

## 2. Target System Performance Calculation Patterns

### Target Models Structure

#### Target Model (`app/models/target.py`)
- [`target_amount`](app/models/target.py:19): Base monthly target
- [`carried_over_amount`](app/models/target.py:20): Unmet target from previous month
- [`adjusted_target_amount`](app/models/target.py:21): Final target (base + carry-over)

#### Target Achievement Model (`app/models/target_achievement.py`)
- [`achieved_amount`](app/models/target_achievement.py:19): Actual revenue achieved
- [`target_amount`](app/models/target_achievement.py:20): Target for the period
- [`achievement_percentage`](app/models/target_achievement.py:21): Pre-calculated percentage

### Performance Calculation Methods

#### Current Month Performance (from [`TargetService.get_targets_overview()`](app/services/target.py:149))
```python
# Current month achievement
current_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
    and_(
        TargetAchievement.year == current_year,
        TargetAchievement.month == current_month
    )
).scalar() or 0.0

# Current month target
current_month_target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
    and_(
        Target.year == current_year,
        Target.month == current_month
    )
).scalar() or 0.0

# Performance percentage
achievement_percentage = (current_achievement / current_month_target * 100) if current_month_target > 0 else 0.0
```

#### Year-to-Date Performance (from [`TargetService.calculate_ytd_metrics()`](app/services/target.py:539))
```python
# YTD target (sum of targets up to current month)
ytd_target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
    and_(
        Target.year == year,
        Target.month <= current_month
    )
).scalar() or 0.0

# YTD achievement
ytd_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
    and_(
        TargetAchievement.year == year,
        TargetAchievement.month <= current_month
    )
).scalar() or 0.0
```

## 3. Authentication & Authorization Patterns

### Authentication Flow

All KPI endpoints use the same authentication pattern from [`app/controllers/kpi.py`](app/controllers/kpi.py:18-19):

```python
@router.get("/endpoint", response_model=KPIResponse)
async def endpoint_function(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # JWT-based authentication
):
```

### Authorization & User Isolation

#### User Roles & Access Control
From [`app/utils/security.py`](app/utils/security.py:227-237):
- **Admin/Finance users**: See all data (no isolation)
- **Sales users**: See only their own data (user isolation applied)

#### User Isolation Implementation
From [`app/services/kpi.py`](app/services/kpi.py:105-107):
```python
# Build base query with user isolation
base_query = db.query(Model)
user_filter = get_user_filter_condition(current_user, Model.user_id)
if user_filter is not True:
    base_query = base_query.filter(user_filter)
```

### Revenue Endpoint Authorization Strategy

For revenue endpoints, we should follow the target system pattern:
- **Sales users**: Only see their own revenue data (where `Invoice.sales_person_id == current_user.id`)
- **Admin/Finance users**: See company-wide revenue data
- Use [`get_current_active_user`](app/utils/security.py:188) for endpoints requiring active user status

## 4. Database Query Patterns for Aggregation

### Monthly Data Aggregation Pattern

From [`TargetService.get_monthly_data()`](app/services/target.py:430-489):
```python
for month in range(1, 13):
    # Get data for each month
    result = self.db.query(func.sum(Model.amount_field)).filter(
        and_(
            Model.year_field == year,
            Model.month_field == month
        )
    ).scalar() or 0.0
    
    monthly_data.append({
        "month": month,
        "month_name": month_names[month - 1],
        "amount": float(result)
    })
```

### Date-based Aggregation for Revenue

Revenue queries should use:
```python
# For monthly aggregation
extract('year', Invoice.issue_date) == year
extract('month', Invoice.issue_date) == month

# For daily aggregation (today's revenue)
Invoice.issue_date == date.today()
```

### Timezone Handling

From [`app/services/kpi.py`](app/services/kpi.py:25-44), the system uses Jakarta timezone:
```python
jakarta_tz = pytz.timezone('Asia/Jakarta')
now_jakarta = datetime.now(jakarta_tz)

# Convert to UTC for database queries
start_current_utc = start_current.astimezone(pytz.UTC)
```

## 5. Response Schema Patterns

### KPI Response Schema (`app/schemas/kpi.py`)

The existing [`KPIResponse`](app/schemas/kpi.py:8) schema provides:
```python
class KPIResponse(BaseModel):
    total: int                      # Total count for the current period
    growth_percentage: float        # Growth percentage vs previous period
    previous_month_total: int       # Previous period total
    period: str                     # Period description (e.g., "January 2025")
```

### Target Performance Schema Patterns

From [`app/schemas/target.py`](app/schemas/target.py):

#### Monthly Data Format ([`MonthlyData`](app/schemas/target.py:45))
```python
class MonthlyData(BaseModel):
    month: int
    month_name: str
    target_amount: float
    achieved_amount: float
    achievement_percentage: float
    carried_over_amount: float
```

#### Performance Metrics ([`YTDMetrics`](app/schemas/target.py:72))
```python
class YTDMetrics(BaseModel):
    ytd_target: float
    ytd_achievement: float
    ytd_percentage: float
```

## 6. Recommended Implementation Strategy

### New Schema Designs

#### 1. Monthly Revenue Response
```python
class MonthlyRevenueResponse(BaseModel):
    year: int
    monthly_data: List[Dict[str, Any]]  # Array of 12 months
    total_yearly_revenue: float
    currency: str = "IDR"
    
class MonthlyRevenueData(BaseModel):
    month: int
    month_name: str
    revenue: float
```

#### 2. Current Month Performance Response
```python
class CurrentMonthPerformanceResponse(BaseModel):
    month: int
    month_name: str
    target: float
    revenue: float
    todays_revenue: float
    performance_percentage: float
    days_remaining: int
    period: str  # "January 2025"
```

#### 3. Current Year Performance Response
```python
class CurrentYearPerformanceResponse(BaseModel):
    year: int
    target: float
    revenue: float
    performance_percentage: float
    months_completed: int
    period: str  # "2025"
```

### Database Query Optimization

1. **Use Indexes**: Ensure indexes exist on `invoice.issue_date`, `invoice.sales_person_id`, `invoice.status`
2. **Aggregation**: Use SQLAlchemy's `func.sum()` for efficient aggregation
3. **Filtering**: Always filter by `invoice.status = 'paid'` for revenue recognition
4. **User Isolation**: Apply appropriate user filtering based on role

### Service Layer Organization

Create new [`RevenueService`](app/services/revenue.py) following the established patterns:
- Static methods for each calculation
- Consistent error handling with HTTPException
- Jakarta timezone handling
- User isolation support

### Controller Layer

Create endpoints in [`app/controllers/revenue.py`](app/controllers/revenue.py):
- Follow existing authentication patterns
- Use consistent error handling
- Apply appropriate user authorization
- Return structured responses

## 7. Key Integration Points

### With Existing Systems

1. **Target System Integration**: Revenue calculations should align with target achievement calculations
2. **KPI System Consistency**: Follow same timezone handling and user isolation patterns
3. **User Management**: Leverage existing role-based access control
4. **Database Models**: Use existing Invoice model without modifications

### Error Handling

Follow the established pattern from [`app/controllers/kpi.py`](app/controllers/kpi.py:24-30):
```python
try:
    return ServiceClass.method_name(db=db, current_user=current_user)
except Exception as e:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error retrieving data: {str(e)}"
    )
```

## 8. Implementation Checklist

### Phase 1: Service Layer
- [ ] Create `RevenueService` class
- [ ] Implement monthly revenue calculation
- [ ] Implement current month performance calculation
- [ ] Implement current year performance calculation
- [ ] Add user isolation support
- [ ] Add timezone handling

### Phase 2: Schema Layer
- [ ] Create revenue response schemas
- [ ] Add validation and field descriptions
- [ ] Include currency formatting

### Phase 3: Controller Layer
- [ ] Create revenue controller endpoints
- [ ] Add authentication/authorization
- [ ] Implement error handling
- [ ] Add API documentation

### Phase 4: Testing & Integration
- [ ] Unit tests for service methods
- [ ] Integration tests for endpoints
- [ ] Performance testing with large datasets
- [ ] User role-based access testing

---

**Generated:** 2025-01-09 11:58 (Jakarta Time)

**Analysis Scope:** Complete codebase review for revenue endpoint implementation guidance

**Next Steps:** Switch to Code mode for implementation based on this architectural analysis