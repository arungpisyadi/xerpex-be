#!/bin/bash
# Script to fix supervisor spawn error

# Set error handling
set -e
echo "Starting supervisor fix..."

# Check if supervisor is installed
if ! command -v supervisorctl &> /dev/null; then
    echo "Supervisor is not installed. Installing..."
    sudo apt update
    sudo apt install -y supervisor
    sudo systemctl enable supervisor
    sudo systemctl start supervisor
fi

# Check supervisor logs
echo "Checking supervisor logs..."
sudo tail -n 50 /var/log/supervisor/supervisord.log

# Create a backup of the current supervisor configuration
echo "Creating backup of supervisor configuration..."
sudo mkdir -p /etc/supervisor/conf.d/backup
sudo cp /etc/supervisor/conf.d/xerpex.conf /etc/supervisor/conf.d/backup/xerpex.conf.bak || echo "No existing configuration to backup."

# Create a new supervisor configuration
echo "Creating new supervisor configuration..."
sudo tee /etc/supervisor/conf.d/xerpex.conf > /dev/null << 'EOF'
[program:xerpex]
command=/opt/xerpex/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/opt/xerpex
user=xerpex
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/supervisor/xerpex-stderr.log
stdout_logfile=/var/log/supervisor/xerpex-stdout.log
environment=PYTHONUNBUFFERED=1
EOF

# Create log directory if it doesn't exist
echo "Ensuring log directory exists..."
sudo mkdir -p /var/log/supervisor
sudo chmod 755 /var/log/supervisor

# Check if the xerpex user exists
if ! id -u xerpex &>/dev/null; then
    echo "User 'xerpex' does not exist. Creating..."
    sudo useradd -m -s /bin/bash xerpex
    sudo mkdir -p /opt/xerpex
    sudo chown -R xerpex:xerpex /opt/xerpex
fi

# Check if the virtual environment exists
if [ ! -d "/opt/xerpex/venv" ]; then
    echo "Virtual environment not found. Creating..."
    sudo su - xerpex -c "cd /opt/xerpex && python3 -m venv venv"
    sudo su - xerpex -c "cd /opt/xerpex && source venv/bin/activate && pip install -r requirements.txt"
fi

# Check if the application files exist
if [ ! -f "/opt/xerpex/app/main.py" ]; then
    echo "Application files not found. Please ensure the application is properly installed in /opt/xerpex."
    exit 1
fi

# Reload supervisor configuration
echo "Reloading supervisor configuration..."
sudo supervisorctl reread
sudo supervisorctl update

# Try to start the service
echo "Starting the service..."
sudo supervisorctl start xerpex || {
    echo "Failed to start service. Checking for more detailed errors..."
    sudo cat /var/log/supervisor/xerpex-stderr.log
    
    echo "Trying alternative approach..."
    # Try running the command directly to see if there are any issues
    sudo su - xerpex -c "cd /opt/xerpex && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000" &
    
    # Wait a moment
    sleep 5
    
    # Check if it's running
    if pgrep -f "uvicorn app.main:app" > /dev/null; then
        echo "Application is running directly. There might be an issue with supervisor configuration."
        echo "Killing the direct process..."
        sudo pkill -f "uvicorn app.main:app"
        
        # Try with a simpler supervisor configuration
        echo "Creating simplified supervisor configuration..."
        sudo tee /etc/supervisor/conf.d/xerpex.conf > /dev/null << 'EOF'
[program:xerpex]
command=/bin/bash -c "cd /opt/xerpex && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
directory=/opt/xerpex
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/xerpex-stderr.log
stdout_logfile=/var/log/supervisor/xerpex-stdout.log
EOF
        
        # Reload and try again
        sudo supervisorctl reread
        sudo supervisorctl update
        sudo supervisorctl start xerpex
    else
        echo "Application failed to run directly. There might be an issue with the application itself."
    fi
}

# Check the status
echo "Checking service status..."
sudo supervisorctl status xerpex

echo "Fix completed. If the service is still not starting, check the logs for more details:"
echo "sudo cat /var/log/supervisor/xerpex-stderr.log"