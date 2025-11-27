"""
Comprehensive tests for sales user access to customer data in the XerpeX ERP System

This test suite verifies that sales users can access all customer data without user isolation,
while ensuring that admin users retain full access and regular users remain isolated to their own data.
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.customer import (
    create_customer, update_customer, get_customer, get_customers,
    delete_customer, get_customer_count, search_customers_by_name
)
from app.utils.security import should_apply_user_isolation


def create_test_user_with_role(db: Session, role: str, username_suffix: str = "") -> User:
    """
    Helper function to create a test user with specific role
    
    Args:
        db: Database session
        role: User role (admin, sales, user, etc.)
        username_suffix: Optional suffix to make username unique
        
    Returns:
        User: Created user
    """
    username = f"test{role}{username_suffix}"
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        full_name=f"Test {role.capitalize()} User",
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_customer_for_user(
    db: Session, 
    user: User, 
    name_suffix: str = ""
) -> Customer:
    """
    Helper function to create a test customer for a specific user
    
    Args:
        db: Database session
        user: User who owns the customer
        name_suffix: Optional suffix to make customer name unique
        
    Returns:
        Customer: Created customer
    """
    customer_data = CustomerCreate(
        name=f"Customer {user.username} {name_suffix}",
        email=f"customer_{user.username}_{name_suffix}@example.com",
        phone_number=f"0812-{user.id:04d}-{hash(name_suffix) % 10000:04d}",
        address=f"Address for {user.username}",
        billing_address=f"Billing Address for {user.username}"
    )
    return create_customer(db, customer_data, user)


class TestSalesUserIsolation:
    """Test user isolation behavior for sales users"""
    
    def test_should_apply_user_isolation_sales_user(self, db: Session):
        """
        Test that should_apply_user_isolation returns False for sales users
        """
        sales_user = create_test_user_with_role(db, "sales")
        
        # Sales users should NOT have isolation applied
        assert should_apply_user_isolation(sales_user) is False
    
    def test_should_apply_user_isolation_admin_user(self, db: Session):
        """
        Test that should_apply_user_isolation returns False for admin users
        """
        admin_user = create_test_user_with_role(db, "admin")
        
        # Admin users should NOT have isolation applied
        assert should_apply_user_isolation(admin_user) is False
    
    def test_should_apply_user_isolation_regular_user(self, db: Session):
        """
        Test that should_apply_user_isolation returns True for regular users
        """
        regular_user = create_test_user_with_role(db, "user")
        
        # Regular users SHOULD have isolation applied
        assert should_apply_user_isolation(regular_user) is True


class TestSalesCustomerAccess:
    """Test sales user access to customer data"""
    
    def test_sales_can_view_all_customers(self, db: Session):
        """
        Test that sales user can view customers created by other users
        """
        # Create users
        sales_user = create_test_user_with_role(db, "sales", "_view")
        regular_user_1 = create_test_user_with_role(db, "user", "_1")
        regular_user_2 = create_test_user_with_role(db, "user", "_2")
        
        # Create customers owned by different users
        customer_1 = create_test_customer_for_user(db, regular_user_1, "1")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "2")
        customer_3 = create_test_customer_for_user(db, sales_user, "3")
        
        # Sales user should see all customers
        all_customers = get_customers(db, sales_user)
        customer_ids = [c.id for c in all_customers]
        
        assert customer_1.id in customer_ids, "Sales user should see customer from regular_user_1"
        assert customer_2.id in customer_ids, "Sales user should see customer from regular_user_2"
        assert customer_3.id in customer_ids, "Sales user should see their own customer"
        assert len(all_customers) >= 3, "Sales user should see at least 3 customers"
    
    def test_sales_can_get_specific_customer_by_id(self, db: Session):
        """
        Test that sales user can get a specific customer created by another user
        """
        # Create users
        sales_user = create_test_user_with_role(db, "sales", "_get")
        regular_user = create_test_user_with_role(db, "user", "_get")
        
        # Create customer owned by regular user
        customer = create_test_customer_for_user(db, regular_user, "get_test")
        
        # Sales user should be able to get this customer
        retrieved_customer = get_customer(db, customer.id, sales_user)
        
        assert retrieved_customer is not None, "Sales user should be able to get customer"
        assert retrieved_customer.id == customer.id
        assert retrieved_customer.user_id == regular_user.id
        assert retrieved_customer.name == customer.name
    
    def test_sales_can_update_other_users_customers(self, db: Session):
        """
        Test that sales user can update customers created by other users
        """
        # Create users
        sales_user = create_test_user_with_role(db, "sales", "_update")
        regular_user = create_test_user_with_role(db, "user", "_update")
        
        # Create customer owned by regular user
        customer = create_test_customer_for_user(db, regular_user, "update_test")
        original_name = customer.name
        
        # Sales user updates the customer
        update_data = CustomerUpdate(
            name="Updated by Sales User",
            phone_number="+62 813 9999 8888"
        )
        updated_customer = update_customer(db, customer.id, update_data, sales_user)
        
        assert updated_customer is not None, "Sales user should be able to update customer"
        assert updated_customer.id == customer.id
        assert updated_customer.name == "Updated by Sales User"
        assert updated_customer.phone_number == "6281399998888"
        assert updated_customer.user_id == regular_user.id  # Owner should not change
    
    def test_sales_can_search_all_customers(self, db: Session):
        """
        Test that sales user can search across all customers regardless of owner
        """
        # Create users
        sales_user = create_test_user_with_role(db, "sales", "_search")
        regular_user_1 = create_test_user_with_role(db, "user", "_search1")
        regular_user_2 = create_test_user_with_role(db, "user", "_search2")
        
        # Create customers with searchable names
        customer_1 = create_test_customer_for_user(db, regular_user_1, "UniqueSearch1")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "UniqueSearch2")
        
        # Sales user searches for "UniqueSearch"
        search_results = get_customers(db, sales_user, search="UniqueSearch")
        search_ids = [c.id for c in search_results]
        
        assert customer_1.id in search_ids, "Sales user should find customer from user 1"
        assert customer_2.id in search_ids, "Sales user should find customer from user 2"
        assert len(search_results) >= 2, "Sales user should find at least 2 matching customers"
    
    def test_sales_can_search_by_name_autocomplete(self, db: Session):
        """
        Test that sales user can use name search/autocomplete across all customers
        """
        # Create users
        sales_user = create_test_user_with_role(db, "sales", "_autocomplete")
        regular_user_1 = create_test_user_with_role(db, "user", "_autocomplete1")
        regular_user_2 = create_test_user_with_role(db, "user", "_autocomplete2")
        
        # Create customers with specific names
        customer_1 = create_test_customer_for_user(db, regular_user_1, "AutoComplete")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "AutoComplete")
        
        # Sales user searches by name
        search_results = search_customers_by_name(db, "AutoComplete", sales_user, limit=10)
        search_ids = [c.id for c in search_results]
        
        assert customer_1.id in search_ids, "Sales user should find customer 1 in autocomplete"
        assert customer_2.id in search_ids, "Sales user should find customer 2 in autocomplete"
    
    def test_sales_sees_correct_customer_count(self, db: Session):
        """
        Test that sales user sees total customer count, not filtered count
        """
        # Create users
        sales_user = create_test_user_with_role(db, "sales", "_count")
        regular_user_1 = create_test_user_with_role(db, "user", "_count1")
        regular_user_2 = create_test_user_with_role(db, "user", "_count2")
        
        # Get initial count
        initial_count = get_customer_count(db, sales_user)
        
        # Create customers owned by different users
        create_test_customer_for_user(db, regular_user_1, "count1")
        create_test_customer_for_user(db, regular_user_2, "count2")
        create_test_customer_for_user(db, sales_user, "count3")
        
        # Sales user should see total count (all 3 new customers)
        final_count = get_customer_count(db, sales_user)
        
        assert final_count == initial_count + 3, "Sales user should see total count of all customers"


class TestAdminUserAccess:
    """Test that admin users still have full access (regression test)"""
    
    def test_admin_still_has_full_access(self, db: Session):
        """
        Test that admin user can access all customers (regression test)
        """
        # Create users
        admin_user = create_test_user_with_role(db, "admin", "_admin_access")
        regular_user_1 = create_test_user_with_role(db, "user", "_admin1")
        regular_user_2 = create_test_user_with_role(db, "user", "_admin2")
        
        # Create customers owned by different users
        customer_1 = create_test_customer_for_user(db, regular_user_1, "admin_test1")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "admin_test2")
        customer_3 = create_test_customer_for_user(db, admin_user, "admin_test3")
        
        # Admin should see all customers
        all_customers = get_customers(db, admin_user)
        customer_ids = [c.id for c in all_customers]
        
        assert customer_1.id in customer_ids, "Admin should see customer from user 1"
        assert customer_2.id in customer_ids, "Admin should see customer from user 2"
        assert customer_3.id in customer_ids, "Admin should see their own customer"
    
    def test_admin_can_update_any_customer(self, db: Session):
        """
        Test that admin user can update any customer (regression test)
        """
        # Create users
        admin_user = create_test_user_with_role(db, "admin", "_admin_update")
        regular_user = create_test_user_with_role(db, "user", "_admin_update")
        
        # Create customer owned by regular user
        customer = create_test_customer_for_user(db, regular_user, "admin_update")
        
        # Admin updates the customer
        update_data = CustomerUpdate(name="Updated by Admin")
        updated_customer = update_customer(db, customer.id, update_data, admin_user)
        
        assert updated_customer is not None
        assert updated_customer.name == "Updated by Admin"
        assert updated_customer.user_id == regular_user.id
    
    def test_admin_sees_total_count(self, db: Session):
        """
        Test that admin user sees total customer count (regression test)
        """
        # Create users
        admin_user = create_test_user_with_role(db, "admin", "_admin_count")
        regular_user_1 = create_test_user_with_role(db, "user", "_admin_count1")
        regular_user_2 = create_test_user_with_role(db, "user", "_admin_count2")
        
        # Get initial count
        initial_count = get_customer_count(db, admin_user)
        
        # Create customers
        create_test_customer_for_user(db, regular_user_1, "admin_c1")
        create_test_customer_for_user(db, regular_user_2, "admin_c2")
        create_test_customer_for_user(db, admin_user, "admin_c3")
        
        # Admin should see all
        final_count = get_customer_count(db, admin_user)
        
        assert final_count == initial_count + 3


class TestRegularUserIsolation:
    """Test that non-sales/admin users still have user isolation (regression test)"""
    
    def test_regular_user_still_isolated(self, db: Session):
        """
        Test that regular users can only see their own customers
        """
        # Create users
        regular_user_1 = create_test_user_with_role(db, "user", "_isolated1")
        regular_user_2 = create_test_user_with_role(db, "user", "_isolated2")
        
        # Create customers
        customer_1 = create_test_customer_for_user(db, regular_user_1, "isolated1")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "isolated2")
        
        # User 1 should only see their own customer
        user1_customers = get_customers(db, regular_user_1)
        user1_ids = [c.id for c in user1_customers]
        
        assert customer_1.id in user1_ids, "User 1 should see their own customer"
        assert customer_2.id not in user1_ids, "User 1 should NOT see User 2's customer"
    
    def test_regular_user_cannot_get_other_users_customer(self, db: Session):
        """
        Test that regular users cannot get customers belonging to other users
        """
        # Create users
        regular_user_1 = create_test_user_with_role(db, "user", "_get_isolated1")
        regular_user_2 = create_test_user_with_role(db, "user", "_get_isolated2")
        
        # Create customer owned by user 2
        customer_2 = create_test_customer_for_user(db, regular_user_2, "get_isolated")
        
        # User 1 tries to get user 2's customer
        retrieved_customer = get_customer(db, customer_2.id, regular_user_1)
        
        assert retrieved_customer is None, "User 1 should NOT be able to get User 2's customer"
    
    def test_regular_user_cannot_update_other_users_customer(self, db: Session):
        """
        Test that regular users cannot update customers belonging to other users
        """
        # Create users
        regular_user_1 = create_test_user_with_role(db, "user", "_update_isolated1")
        regular_user_2 = create_test_user_with_role(db, "user", "_update_isolated2")
        
        # Create customer owned by user 2
        customer_2 = create_test_customer_for_user(db, regular_user_2, "update_isolated")
        
        # User 1 tries to update user 2's customer
        update_data = CustomerUpdate(name="Hacked by User 1")
        
        with pytest.raises(Exception):  # Should raise HTTPException
            update_customer(db, customer_2.id, update_data, regular_user_1)
    
    def test_regular_user_sees_only_their_count(self, db: Session):
        """
        Test that regular users only see their own customer count
        """
        # Create users
        regular_user_1 = create_test_user_with_role(db, "user", "_count_isolated1")
        regular_user_2 = create_test_user_with_role(db, "user", "_count_isolated2")
        
        # Get initial count for user 1
        initial_count = get_customer_count(db, regular_user_1)
        
        # Create customers
        create_test_customer_for_user(db, regular_user_1, "count_i1")
        create_test_customer_for_user(db, regular_user_1, "count_i2")
        create_test_customer_for_user(db, regular_user_2, "count_i3")  # This one shouldn't be counted
        
        # User 1 should only see their own count (+2)
        final_count = get_customer_count(db, regular_user_1)
        
        assert final_count == initial_count + 2, "User 1 should only see their own 2 customers"
    
    def test_regular_user_search_is_isolated(self, db: Session):
        """
        Test that regular user search only returns their own customers
        """
        # Create users
        regular_user_1 = create_test_user_with_role(db, "user", "_search_isolated1")
        regular_user_2 = create_test_user_with_role(db, "user", "_search_isolated2")
        
        # Create customers with same search term
        customer_1 = create_test_customer_for_user(db, regular_user_1, "SearchIsolated")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "SearchIsolated")
        
        # User 1 searches
        search_results = get_customers(db, regular_user_1, search="SearchIsolated")
        search_ids = [c.id for c in search_results]
        
        assert customer_1.id in search_ids, "User 1 should find their own customer"
        assert customer_2.id not in search_ids, "User 1 should NOT find User 2's customer"


class TestFinanceUserAccess:
    """Test that finance users also have full access like sales and admin"""
    
    def test_finance_user_can_view_all_customers(self, db: Session):
        """
        Test that finance user can view all customers
        """
        # Create users
        finance_user = create_test_user_with_role(db, "finance", "_finance_view")
        regular_user_1 = create_test_user_with_role(db, "user", "_finance1")
        regular_user_2 = create_test_user_with_role(db, "user", "_finance2")
        
        # Create customers
        customer_1 = create_test_customer_for_user(db, regular_user_1, "finance1")
        customer_2 = create_test_customer_for_user(db, regular_user_2, "finance2")
        
        # Finance user should see all customers
        all_customers = get_customers(db, finance_user)
        customer_ids = [c.id for c in all_customers]
        
        assert customer_1.id in customer_ids, "Finance user should see customer from user 1"
        assert customer_2.id in customer_ids, "Finance user should see customer from user 2"
    
    def test_finance_user_no_isolation(self, db: Session):
        """
        Test that finance users do not have isolation applied
        """
        finance_user = create_test_user_with_role(db, "finance", "_no_isolation")
        
        # Finance users should NOT have isolation applied
        assert should_apply_user_isolation(finance_user) is False


class TestCrossRoleCustomerOperations:
    """Test customer operations across different user roles"""
    
    def test_customer_visibility_by_role(self, db: Session):
        """
        Test comprehensive customer visibility across all roles
        """
        # Create users of different roles
        admin_user = create_test_user_with_role(db, "admin", "_visibility")
        sales_user = create_test_user_with_role(db, "sales", "_visibility")
        finance_user = create_test_user_with_role(db, "finance", "_visibility")
        regular_user_1 = create_test_user_with_role(db, "user", "_visibility1")
        regular_user_2 = create_test_user_with_role(db, "user", "_visibility2")
        
        # Create customers owned by different users
        customer_admin = create_test_customer_for_user(db, admin_user, "vis_admin")
        customer_sales = create_test_customer_for_user(db, sales_user, "vis_sales")
        customer_finance = create_test_customer_for_user(db, finance_user, "vis_finance")
        customer_user1 = create_test_customer_for_user(db, regular_user_1, "vis_user1")
        customer_user2 = create_test_customer_for_user(db, regular_user_2, "vis_user2")
        
        all_customer_ids = [customer_admin.id, customer_sales.id, customer_finance.id, 
                           customer_user1.id, customer_user2.id]
        
        # Admin should see all
        admin_customers = get_customers(db, admin_user)
        admin_ids = [c.id for c in admin_customers]
        for cid in all_customer_ids:
            assert cid in admin_ids, f"Admin should see customer {cid}"
        
        # Sales should see all
        sales_customers = get_customers(db, sales_user)
        sales_ids = [c.id for c in sales_customers]
        for cid in all_customer_ids:
            assert cid in sales_ids, f"Sales should see customer {cid}"
        
        # Finance should see all
        finance_customers = get_customers(db, finance_user)
        finance_ids = [c.id for c in finance_customers]
        for cid in all_customer_ids:
            assert cid in finance_ids, f"Finance should see customer {cid}"
        
        # Regular user 1 should only see their own
        user1_customers = get_customers(db, regular_user_1)
        user1_ids = [c.id for c in user1_customers]
        assert customer_user1.id in user1_ids, "User 1 should see their own customer"
        assert customer_user2.id not in user1_ids, "User 1 should NOT see User 2's customer"