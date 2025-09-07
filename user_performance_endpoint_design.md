# User Performance Endpoint Design for Bar Chart Visualization

## Overview
This document outlines the design for a new API endpoint that provides user performance data optimized for bar chart visualization. The endpoint will build upon the existing company performance functionality while restructuring the data to be chart-ready.

## Existing Company Performance Analysis

### Current Endpoint
- **Path**: `GET /targets/company-performance`
- **Parameters**: `year` (optional, defaults to current year)
- **Authentication**: Requires active user
- **Response Schema**: `CompanyPerformance` with aggregated totals and user performance list

### Data Sources
- **Models**: `Target`, `TargetAchievement`, `User`
- **Service**: `TargetService.get_company_performance()`
- **Calculation**: Aggregates targets and achievements for all sales users

## New Endpoint Design

### Endpoint Specifications
- **Path**: `GET /targets/user-performances`
- **Method**: `GET`
- **Parameters**:
  - `year`: `int` (required) - Year for performance data
  - `user_id`: `Optional[int]` (optional) - Filter for specific user; if not provided, returns all sales users

### Authentication & Authorization
- Requires authenticated active user (same as existing endpoints)
- No additional role restrictions beyond existing user authentication
- Uses `get_current_active_user` dependency

### Response Schema Design

#### Primary Response Model: `UserPerformanceChart`
```python
class UserPerformanceChart(BaseModel):
    year: int
    chart_data: ChartData
    users: List[UserPerformanceDetail]
    total_users: int
    generated_at: datetime
```

#### Chart Data Model: `ChartData`
```python
class ChartData(BaseModel):
    labels: List[str]  # User names/full names
    datasets: List[ChartDataset]
```

#### Chart Dataset Model: `ChartDataset`
```python
class ChartDataset(BaseModel):
    label: str  # "Target Amount" or "Achieved Amount"
    data: List[float]  # Corresponding values for each user
    backgroundColor: Optional[str] = None
    borderColor: Optional[str] = None
```

#### User Performance Detail Model: `UserPerformanceDetail`
```python
class UserPerformanceDetail(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str]
    target_amount: float
    achieved_amount: float
    achievement_percentage: float
    months_with_data: int  # Number of months with targets/achievements
```

### Sample Response
```json
{
  "year": 2024,
  "chart_data": {
    "labels": ["John Doe", "Jane Smith", "Bob Johnson"],
    "datasets": [
      {
        "label": "Target Amount",
        "data": [15000.00, 20000.00, 18000.00],
        "backgroundColor": "rgba(54, 162, 235, 0.5)",
        "borderColor": "rgba(54, 162, 235, 1)"
      },
      {
        "label": "Achieved Amount",
        "data": [12000.00, 18500.00, 16000.00],
        "backgroundColor": "rgba(75, 192, 192, 0.5)",
        "borderColor": "rgba(75, 192, 192, 1)"
      }
    ]
  },
  "users": [
    {
      "user_id": 1,
      "username": "john_doe",
      "full_name": "John Doe",
      "target_amount": 15000.00,
      "achieved_amount": 12000.00,
      "achievement_percentage": 80.0,
      "months_with_data": 12
    },
    {
      "user_id": 2,
      "username": "jane_smith",
      "full_name": "Jane Smith",
      "target_amount": 20000.00,
      "achieved_amount": 18500.00,
      "achievement_percentage": 92.5,
      "months_with_data": 12
    },
    {
      "user_id": 3,
      "username": "bob_johnson",
      "full_name": "Bob Johnson",
      "target_amount": 18000.00,
      "achieved_amount": 16000.00,
      "achievement_percentage": 88.9,
      "months_with_data": 10
    }
  ],
  "total_users": 3,
  "generated_at": "2024-09-07T05:22:38.660Z"
}
```

## Data Transformation Logic

### Service Method: `get_user_performance_chart()`
Location: `app/services/target.py`

```python
def get_user_performance_chart(self, year: int, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get user performance data formatted for bar chart visualization

    Args:
        year: Year for performance data
        user_id: Optional user ID filter

    Returns:
        Dict containing chart-ready performance data
    """
    # Query logic:
    # 1. Get sales users (filtered by user_id if provided)
    # 2. For each user, aggregate targets and achievements for the year
    # 3. Calculate percentages and format for chart
    # 4. Return structured data
```

### Key Calculations
1. **Target Amount**: Sum of `adjusted_target_amount` from `Target` table for the year
2. **Achieved Amount**: Sum of `achieved_amount` from `TargetAchievement` table for the year
3. **Achievement Percentage**: `(achieved_amount / target_amount) * 100` if target > 0
4. **Months with Data**: Count of months with either targets or achievements

### Database Queries
```sql
-- Get users
SELECT id, username, full_name FROM users WHERE role = 'sales' [AND id = ?]

-- Get user targets
SELECT SUM(adjusted_target_amount) as target_amount
FROM sales_targets
WHERE user_id = ? AND year = ?

-- Get user achievements
SELECT SUM(achieved_amount) as achieved_amount
FROM target_achievements
WHERE user_id = ? AND year = ?
```

## Integration Points

### Existing Services
- **TargetService**: Reuse existing methods for data aggregation
- **Database Session**: Use existing session management
- **Security**: Leverage existing authentication dependencies

### New Components Required
1. **Controller Method**: Add to `app/controllers/target.py`
2. **Service Method**: Add `get_user_performance_chart()` to `TargetService`
3. **Schema Models**: Add new Pydantic models to `app/schemas/target.py`

### Router Integration
Add to existing `targets_router` in `app/controllers/target.py`:
```python
@targets_router.get("/user-performances", response_model=UserPerformanceChart)
async def get_user_performance_chart(
    year: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
```

## Error Handling
- **Invalid Year**: Return 400 if year is not a valid integer
- **No Data**: Return empty chart data if no users/targets found
- **Database Errors**: Return 500 with appropriate error message
- **Authentication Errors**: Handled by existing dependencies

## Performance Considerations
- **Caching**: Consider caching for frequently accessed years
- **Pagination**: For large number of users, consider pagination (though unlikely for sales teams)
- **Database Optimization**: Use existing indexes on user_id, year, month

## Testing Strategy
- **Unit Tests**: Test service method with mock data
- **Integration Tests**: Test full endpoint with database
- **Edge Cases**: Empty data, single user, invalid parameters

## Future Enhancements
- **Monthly Breakdown**: Option to return monthly data instead of yearly totals
- **Date Range Filtering**: Support for custom date ranges
- **Chart Customization**: Parameters for chart colors, labels
- **Export Formats**: Support for CSV/Excel export of the data

## Implementation Checklist
- [ ] Add new schema models to `app/schemas/target.py`
- [ ] Implement `get_user_performance_chart()` in `TargetService`
- [ ] Add controller method to `app/controllers/target.py`
- [ ] Update router with new endpoint
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Update API documentation
- [ ] Test with frontend chart library (Chart.js, etc.)