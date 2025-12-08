"""
Seeder script for generating test data for customers, quotes, and surveys
with Indonesian names and phone numbers starting with 62.
"""

import random
from datetime import datetime, date, timedelta
from faker import Faker
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.customer import Customer
from app.models.quote import Quote, QuoteItem, QuoteVilla
from app.models.survey import Survey
from app.models.user import User
from app.models.package import Package
from app.models.villa import Villa
from app.models.salesmen import Salesmen

# Initialize Faker with Indonesian locale
fake = Faker('id_ID')

# Common Indonesian names
INDONESIAN_NAMES = [
    "Budi Santoso", "Siti Rahayu", "Agus Prasetyo", "Dewi Lestari", "Joko Susilo",
    "Rina Wijaya", "Eko Saputra", "Lina Permata", "Hendra Gunawan", "Maya Sari",
    "Andi Setiawan", "Tina Kartika", "Rudi Hartono", "Sari Utami", "Doni Putra",
    "Nia Permata", "Fajar Nugroho", "Dian Ayu", "Galih Wibowo", "Rani Fitriani",
    "Bayu Pamungkas", "Citra Dewi", "Dimas Aditya", "Eka Putri", "Fandi Rahman",
    "Gita Permata", "Hadi Kurniawan", "Indah Lestari", "Joni Saputra", "Kartika Sari",
    "Luki Setiawan", "Mira Wijaya", "Nando Gunawan", "Oktavia Lestari", "Pandu Susilo",
    "Qori Ayu", "Rangga Putra", "Sinta Permata", "Taufik Hidayat", "Umi Lestari",
    "Vina Kartika", "Wawan Setiawan", "Xena Dewi", "Yudi Aditya", "Zahra Ayu",
    "Ahmad Subhan", "Bella Sari", "Cahyo Nugroho", "Dewi Kartika", "Eka Wijaya",
    "Fani Permata", "Gita Lestari", "Hana Sari", "Iwan Setiawan", "Jihan Ayu",
    "Kiki Gunawan", "Lala Dewi", "Maman Saputra", "Nana Lestari", "Oki Putra",
    "Puti Ayu", "Qori Sari", "Rara Permata", "Sasa Wijaya", "Tata Lestari",
    "Ucup Setiawan", "Vina Ayu", "Wati Dewi", "Xena Sari", "Yaya Permata",
    "Zaki Gunawan", "Aulia Lestari", "Bima Setiawan", "Cici Ayu", "Dedi Saputra",
    "Euis Dewi", "Fajar Lestari", "Gina Sari", "Hadi Ayu", "Ika Permata",
    "Joko Wijaya", "Kiki Lestari", "Lala Setiawan", "Mira Ayu", "Nana Dewi",
    "Oki Saputra", "Puti Lestari", "Qori Setiawan", "Rara Ayu", "Sasa Dewi",
    "Tata Saputra", "Umi Lestari", "Vina Setiawan", "Wati Ayu", "Xena Dewi",
    "Yaya Saputra", "Zahra Lestari", "Ahmad Wijaya", "Bella Setiawan", "Cahyo Ayu",
    "Dewi Saputra", "Eka Lestari", "Fani Setiawan", "Gita Ayu", "Hana Dewi",
    "Iwan Lestari", "Jihan Setiawan", "Kiki Ayu", "Lala Dewi", "Maman Lestari",
    "Nana Setiawan", "Oki Ayu", "Puti Dewi", "Qori Setiawan", "Rara Lestari",
    "Sasa Ayu", "Tata Dewi", "Ucup Lestari", "Vina Setiawan", "Wati Ayu",
    "Xena Lestari", "Yaya Setiawan", "Zaki Ayu", "Aulia Dewi", "Bima Lestari",
    "Cici Setiawan", "Dedi Ayu", "Euis Lestari", "Fajar Dewi", "Gina Setiawan",
    "Hadi Ayu", "Ika Lestari", "Joko Dewi", "Kiki Setiawan", "Lala Ayu",
    "Mira Lestari", "Nana Dewi", "Oki Setiawan", "Puti Ayu", "Qori Lestari",
    "Rara Dewi", "Sasa Setiawan", "Tata Ayu", "Umi Dewi", "Vina Lestari",
    "Wati Setiawan", "Xena Ayu", "Yaya Lestari", "Zahra Dewi", "Ahmad Setiawan",
    "Bella Ayu", "Cahyo Lestari", "Dewi Setiawan", "Eka Ayu", "Fani Lestari",
    "Gita Dewi", "Hana Setiawan", "Iwan Ayu", "Jihan Lestari", "Kiki Dewi",
    "Lala Setiawan", "Maman Ayu", "Nana Lestari", "Oki Dewi", "Puti Setiawan",
    "Qori Ayu", "Rara Dewi", "Sasa Lestari", "Tata Dewi", "Ucup Ayu",
    "Vina Lestari", "Wati Dewi", "Xena Setiawan", "Yaya Ayu", "Zaki Dewi"
]

def generate_indonesian_phone():
    """Generate Indonesian phone number starting with 62"""
    # Start with 62 (country code)
    phone = "62"
    # Add 8-12 more digits
    for _ in range(8, 12):
        phone += str(random.randint(0, 9))
    return phone

def generate_indonesian_email(name):
    """Generate Indonesian-style email"""
    first_name = name.split()[0].lower()
    domains = ["gmail.com", "yahoo.co.id", "outlook.com", "hotmail.com", "email.com"]
    return f"{first_name}{random.randint(1, 99)}@{random.choice(domains)}"

def generate_indonesian_address():
    """Generate Indonesian-style address"""
    cities = [
        "Jakarta", "Surabaya", "Bandung", "Medan", "Semarang",
        "Makassar", "Palembang", "Denpasar", "Yogyakarta", "Malang",
        "Bekasi", "Depok", "Tangerang", "Bogor", "Batam",
        "Padang", "Bandar Lampung", "Samarinda", "Pontianak", "Manado"
    ]
    streets = [
        "Jl. Merdeka", "Jl. Sudirman", "Jl. Gatot Subroto", "Jl. Thamrin",
        "Jl. Ahmad Yani", "Jl. Diponegoro", "Jl. Pattimura", "Jl. Hayam Wuruk",
        "Jl. Pemuda", "Jl. Veteran", "Jl. MT Haryono", "Jl. Imam Bonjol"
    ]
    return f"{streets[random.randint(0, len(streets)-1)]} No.{random.randint(1, 100)}, {cities[random.randint(0, len(cities)-1)]}"

def get_or_create_user(db: Session):
    """Get or create a test user"""
    user = db.query(User).filter_by(username="testuser").first()
    if not user:
        user = User(
            username="testuser",
            email="testuser@example.com",
            password_hash="hashed_password",  # In real usage, this should be properly hashed
            full_name="Test User",
            role="admin",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_or_create_salesman(db: Session):
    """Get or create a test salesman"""
    salesman = db.query(Salesmen).filter_by(email="sales@example.com").first()
    if not salesman:
        salesman = Salesmen(
            first_name="Sales",
            last_name="Person",
            email="sales@example.com",
            phone_number="6281234567890",
            is_active=True
        )
        db.add(salesman)
        db.commit()
        db.refresh(salesman)
    return salesman

def get_or_create_package(db: Session, user_id: int):
    """Get or create a test package"""
    package = db.query(Package).filter_by(name="Standard Package").first()
    if not package:
        package = Package(
            user_id=user_id,
            name="Standard Package",
            category="Standard",
            type="Regular",
            description="Standard tour package",
            days=3,
            cost_per_pax=1500000.00,
            min_pax=2
        )
        db.add(package)
        db.commit()
        db.refresh(package)
    return package

def get_or_create_villa(db: Session):
    """Get or create a test villa"""
    villa = db.query(Villa).filter_by(name="Standard Villa").first()
    if not villa:
        villa = Villa(
            name="Standard Villa",
            description="Standard villa for testing",
            capacity="4-6 people",
            room_type="Deluxe",
            base_price=2500000.00,
            is_active=True
        )
        db.add(villa)
        db.commit()
        db.refresh(villa)
    return villa

def create_customers(db: Session, user_id: int, count: int):
    """Create customer records"""
    customers = []
    for i in range(count):
        name = random.choice(INDONESIAN_NAMES)
        customer = Customer(
            user_id=user_id,
            name=name,
            email=generate_indonesian_email(name),
            phone_number=generate_indonesian_phone(),
            address=generate_indonesian_address(),
            billing_address=generate_indonesian_address(),
            status=1  # active
        )
        customers.append(customer)
        db.add(customer)

    db.commit()
    return customers

def create_quotes(db: Session, user_id: int, customers: list, package_id: int, villa_id: int, count: int):
    """Create quote records"""
    quotes = []
    for i, customer in enumerate(customers[:count]):
        # Generate quote number
        quote_number = f"QT-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}"

        # Generate random dates
        issue_date = date.today()
        expiry_date = issue_date + timedelta(days=30)
        check_in = issue_date + timedelta(days=random.randint(7, 30))
        check_out = check_in + timedelta(days=random.randint(2, 7))

        quote = Quote(
            user_id=user_id,
            customer_id=customer.id,
            sales_person_id=user_id,  # Use same user as sales person
            quote_number=quote_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            check_in=check_in,
            check_out=check_out,
            status=random.choice(["draft", "sent", "accepted", "declined"]),
            notes=f"Test quote for {customer.name}",
            total=random.uniform(5000000, 20000000),
            tax_total=random.uniform(100000, 500000)
        )
        quotes.append(quote)
        db.add(quote)
        db.commit()
        db.refresh(quote)

        # Create quote items
        pax = random.randint(2, 10)
        unit_price = random.uniform(1000000, 5000000)
        discount = random.uniform(0, 500000)
        line_total = pax * unit_price - discount

        quote_item = QuoteItem(
            quote_id=quote.id,
            package_id=package_id,
            pax=pax,
            unit_price=unit_price,
            discount=discount,
            line_total=line_total
        )
        db.add(quote_item)

        # Create quote villa association
        quote_villa = QuoteVilla(
            quote_id=quote.id,
            villa_id=villa_id
        )
        db.add(quote_villa)

    db.commit()
    return quotes

def create_surveys(db: Session, salesman_id: int, count: int):
    """Create survey records"""
    surveys = []
    for i in range(count):
        name = random.choice(INDONESIAN_NAMES)
        survey = Survey(
            client_name=name,
            email=generate_indonesian_email(name),
            phone_number=generate_indonesian_phone(),
            estimated_paxes=random.randint(2, 20),
            villa_types="Standard, Deluxe, Premium",
            notes=f"Survey for {name}",
            status=random.choice(["new", "contacted", "scheduled", "visited", "quoted"]),
            priority=random.choice(["low", "medium", "high", "urgent"]),
            follow_up_date=date.today() + timedelta(days=random.randint(1, 14)),
            visiting_date=date.today() + timedelta(days=random.randint(15, 30)),
            salesmen_id=salesman_id
        )
        surveys.append(survey)
        db.add(survey)

    db.commit()
    return surveys

def seed_data():
    """Main seeder function"""
    print("Starting seeder...")

    # Generate random count between 300-500
    data_count = random.randint(300, 500)
    print(f"Generating {data_count} records for each entity...")

    db = SessionLocal()

    try:
        # Get or create required entities
        user = get_or_create_user(db)
        salesman = get_or_create_salesman(db)
        package = get_or_create_package(db, user.id)
        villa = get_or_create_villa(db)

        print("Creating customers...")
        customers = create_customers(db, user.id, data_count)

        print("Creating quotes...")
        quotes = create_quotes(db, user.id, customers, package.id, villa.id, data_count)

        print("Creating surveys...")
        surveys = create_surveys(db, salesman.id, data_count)

        print(f"✅ Successfully created:")
        print(f"   - {len(customers)} customers")
        print(f"   - {len(quotes)} quotes")
        print(f"   - {len(surveys)} surveys")

        return True

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
        return False

    finally:
        db.close()

if __name__ == "__main__":
    success = seed_data()
    if success:
        print("Seeder completed successfully!")
    else:
        print("Seeder failed!")