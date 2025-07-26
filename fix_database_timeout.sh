#!/bin/bash
# Script to diagnose and fix database operation timeout

# Set error handling
set -e
echo "Starting database timeout diagnosis..."

# Load environment variables if available
if [ -f .env ]; then
    echo "Found .env file, extracting database credentials..."
    # Extract database credentials directly
    MYSQL_SERVER=$(grep MYSQL_SERVER .env | cut -d '=' -f2)
    MYSQL_USER=$(grep MYSQL_USER .env | cut -d '=' -f2)
    MYSQL_PASSWORD=$(grep MYSQL_PASSWORD .env | cut -d '=' -f2)
    MYSQL_DB=$(grep MYSQL_DB .env | cut -d '=' -f2)
    MYSQL_PORT=$(grep MYSQL_PORT .env | cut -d '=' -f2)
    echo "Loaded database credentials from .env"
elif [ -f .env.staging ]; then
    echo "Found .env.staging file, extracting database credentials..."
    # Extract database credentials directly
    MYSQL_SERVER=$(grep MYSQL_SERVER .env.staging | cut -d '=' -f2)
    MYSQL_USER=$(grep MYSQL_USER .env.staging | cut -d '=' -f2)
    MYSQL_PASSWORD=$(grep MYSQL_PASSWORD .env.staging | cut -d '=' -f2)
    MYSQL_DB=$(grep MYSQL_DB .env.staging | cut -d '=' -f2)
    MYSQL_PORT=$(grep MYSQL_PORT .env.staging | cut -d '=' -f2)
    echo "Loaded database credentials from .env.staging"
else
    echo "No .env file found. Please enter database credentials manually:"
    read -p "MySQL Host: " MYSQL_SERVER
    read -p "MySQL User: " MYSQL_USER
    read -sp "MySQL Password: " MYSQL_PASSWORD
    echo ""
    read -p "MySQL Database: " MYSQL_DB
    read -p "MySQL Port: " MYSQL_PORT
fi

# Display the credentials (without password)
echo "Using database credentials:"
echo "Host: $MYSQL_SERVER"
echo "User: $MYSQL_USER"
echo "Database: $MYSQL_DB"
echo "Port: $MYSQL_PORT"

# Check MySQL connection
echo "Testing MySQL connection..."
if command -v mysql &> /dev/null; then
    if mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" "$MYSQL_DB"; then
        echo "MySQL connection successful!"
    else
        echo "MySQL connection failed. Please check your credentials and server status."
        exit 1
    fi
else
    echo "MySQL client not found. Installing..."
    sudo apt update
    sudo apt install -y mysql-client
    
    # Try again
    if mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" "$MYSQL_DB"; then
        echo "MySQL connection successful!"
    else
        echo "MySQL connection failed. Please check your credentials and server status."
        exit 1
    fi
fi

# Check for slow queries
echo "Checking for slow queries..."
mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW VARIABLES LIKE 'slow_query%';"
mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW VARIABLES LIKE 'long_query_time';"

# Check for locks
echo "Checking for locks..."
mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW OPEN TABLES WHERE In_use > 0;"
mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW PROCESSLIST;"

# Check user table structure
echo "Checking user table structure..."
mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "DESCRIBE user;"

# Check for indexes on user table
echo "Checking for indexes on user table..."
mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW INDEX FROM user;"

# Add indexes if needed
echo "Would you like to add indexes to the email and username columns? (y/n)"
read add_indexes

if [ "$add_indexes" == "y" ]; then
    echo "Adding indexes to user table..."
    
    # Check if indexes already exist
    email_index=$(mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW INDEX FROM user WHERE Column_name='email';" 2>/dev/null | grep -c "email" || true)
    username_index=$(mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "SHOW INDEX FROM user WHERE Column_name='username';" 2>/dev/null | grep -c "username" || true)
    
    # Add email index if it doesn't exist
    if [ "$email_index" -eq 0 ]; then
        echo "Adding index to email column..."
        mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "CREATE INDEX idx_user_email ON user(email);"
    else
        echo "Index on email column already exists."
    fi
    
    # Add username index if it doesn't exist
    if [ "$username_index" -eq 0 ]; then
        echo "Adding index to username column..."
        mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "CREATE INDEX idx_user_username ON user(username);"
    else
        echo "Index on username column already exists."
    fi
    
    echo "Indexes added successfully!"
fi

# Optimize the user table
echo "Would you like to optimize the user table? (y/n)"
read optimize_table

if [ "$optimize_table" == "y" ]; then
    echo "Optimizing user table..."
    mysql -h "$MYSQL_SERVER" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" -e "OPTIMIZE TABLE user;"
    echo "Table optimized successfully!"
fi

# Update the login query to be more efficient
echo "Would you like to update the login query to be more efficient? (y/n)"
read update_query

if [ "$update_query" == "y" ]; then
    echo "Updating login query in app/controllers/auth.py..."
    
    # Create a backup
    cp app/controllers/auth.py app/controllers/auth.py.bak
    
    # Update the query
    sed -i 's/SELECT id, email, password_hash, role FROM user WHERE email = :email OR username = :email/SELECT id, email, password_hash, role FROM user WHERE email = :email/g' app/controllers/auth.py
    
    echo "Login query updated to be more efficient!"
    echo "A backup of the original file was created at app/controllers/auth.py.bak"
fi

# Increase database connection pool size
echo "Would you like to increase the database connection pool size? (y/n)"
read increase_pool

if [ "$increase_pool" == "y" ]; then
    echo "Updating database.py to increase connection pool size..."
    
    # Create a backup
    cp app/database.py app/database.py.bak
    
    # Update the pool size
    sed -i 's/pool_size=10/pool_size=20/g' app/database.py
    sed -i 's/max_overflow=20/max_overflow=40/g' app/database.py
    
    echo "Database connection pool size increased!"
    echo "A backup of the original file was created at app/database.py.bak"
fi

# Restart the application
echo "Would you like to restart the application? (y/n)"
read restart_app

if [ "$restart_app" == "y" ]; then
    echo "Restarting the application..."
    
    # Try supervisor first
    if command -v supervisorctl &> /dev/null; then
        sudo supervisorctl restart xerpex || echo "Failed to restart with supervisor."
    fi
    
    # Try systemd
    if command -v systemctl &> /dev/null; then
        sudo systemctl restart xerpex || echo "Failed to restart with systemd."
    fi
    
    # Try direct restart
    pkill -f "uvicorn app.main:app" || echo "No running uvicorn processes found."
    cd /opt/xerpex || cd .
    source venv/bin/activate || echo "Virtual environment not found."
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
    
    echo "Application restarted!"
fi

echo "Database timeout diagnosis and fixes completed."
echo "Please test the login endpoint again to see if the timeout issue is resolved."