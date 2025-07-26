# Ubuntu 22.04 Deployment Guide for XerpeX ERP System (Without Docker)

This guide provides step-by-step instructions for deploying the XerpeX ERP System on Ubuntu 22.04 using Nginx as a reverse proxy, without using Docker.

## 1. Prepare Ubuntu 22.04 Server

First, ensure your Ubuntu 22.04 server is up-to-date:

```bash
sudo apt update
sudo apt upgrade -y
```

Set the correct timezone:

```bash
sudo timedatectl set-timezone Asia/Jakarta
```

## 2. Install System Dependencies

Install the required system packages:

```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev \
                    nginx supervisor \
                    mysql-client default-libmysqlclient-dev \
                    pkg-config libssl-dev libffi-dev \
                    build-essential git curl
```

If you encounter issues with MySQL client installation later, you may need additional packages:

```bash
sudo apt install -y pkg-config python3-dev default-libmysqlclient-dev build-essential
```

## 3. Set Up Python Environment

Create a dedicated user for the application (optional but recommended):

```bash
sudo useradd -m -s /bin/bash xerpex
sudo passwd xerpex
```

Create the application directory:

```bash
sudo mkdir -p /opt/xerpex
sudo chown xerpex:xerpex /opt/xerpex
```

Switch to the application user and set up a Python virtual environment:

```bash
sudo su - xerpex
cd /opt/xerpex
python3 -m venv venv
source venv/bin/activate
```

## 4. Set Up MySQL Database

Install MySQL server if you're hosting the database on the same server:

```bash
sudo apt install -y mysql-server
```

Secure the MySQL installation:

```bash
sudo mysql_secure_installation
```

Create a database and user for the application:

```bash
sudo mysql -u root -p
```

In the MySQL prompt:

```sql
CREATE DATABASE xerpex_db;
CREATE USER 'xerpex_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON xerpex_db.* TO 'xerpex_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 5. Clone and Configure the Application

Clone the repository (as the application user):

```bash
cd /opt/xerpex
git clone https://your-repository-url.git .
```

Or upload your application files to the server:

```bash
# From your local machine
scp -r /path/to/your/app/* xerpex@your-server-ip:/opt/xerpex/
```

Install the Python dependencies:

```bash
cd /opt/xerpex
source venv/bin/activate
pip install -r requirements.txt
```

## 6. Set Up Environment Variables

Create a `.env` file:

```bash
cd /opt/xerpex
nano .env
```

Add the following content (adjust as needed):

```
# API settings
PROJECT_NAME=XerpeX ERP System
API_V1_STR=/api/v1

# Security settings
SECRET_KEY=your_secure_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8 days

# Database settings
MYSQL_SERVER=localhost
MYSQL_USER=xerpex_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DB=xerpex_db
MYSQL_PORT=3306

# CORS settings
BACKEND_CORS_ORIGINS=["http://localhost:3000", "https://kebunsu-staging.tugugroup.co.id"]

# Sentry settings
SENTRY_DSN=your_sentry_dsn
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_ENABLE=true
```

## 7. Run Database Migrations

Apply the database migrations:

```bash
cd /opt/xerpex
source venv/bin/activate
alembic upgrade head
```

## 8. Configure and Test the Application

Test the application by running it directly:

```bash
cd /opt/xerpex
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Press Ctrl+C to stop the application after testing.

To run the application in detached mode (in the background):

```bash
cd /opt/xerpex
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
```

This will run uvicorn in the background, detached from the terminal. You can check if it's running with:

```bash
ps aux | grep uvicorn
```

To stop the detached uvicorn process:

```bash
pkill -f "uvicorn app.main:app"
```

## 9. Set Up Supervisor

Create a supervisor configuration file:

```bash
sudo nano /etc/supervisor/conf.d/xerpex.conf
```

Add the following content:

```ini
[program:xerpex]
command=/opt/xerpex/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --daemon
directory=/opt/xerpex
user=xerpex
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/xerpex/err.log
stdout_logfile=/var/log/xerpex/out.log
```

Note: The `--daemon` flag runs uvicorn in detached mode. Alternatively, you can use systemd directly instead of supervisor:

```bash
sudo nano /etc/systemd/system/xerpex.service
```

Add the following content:

```ini
[Unit]
Description=XerpeX ERP System
After=network.target

[Service]
User=xerpex
Group=xerpex
WorkingDirectory=/opt/xerpex
Environment="PATH=/opt/xerpex/venv/bin"
ExecStart=/opt/xerpex/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable xerpex
sudo systemctl start xerpex
```

Check the status:

```bash
sudo systemctl status xerpex
```

Create the log directory:

```bash
sudo mkdir -p /var/log/xerpex
sudo chown -R xerpex:xerpex /var/log/xerpex
```

Reload supervisor:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start xerpex
```

## 10. Set Up Nginx

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/xerpex
```

Add the following content:

```nginx
server {
    listen 80;
    server_name kebunsu-api.tugugroup.co.id;
    
    # CORS configuration
    set $cors_origin "";
    
    if ($http_origin ~ '^https?://(kebunsu-staging\.tugugroup\.co\.id)$') {
        set $cors_origin $http_origin;
    }
    
    if ($http_origin ~ '^http://localhost:(3000|8000)$') {
        set $cors_origin $http_origin;
    }
    
    # Add CORS headers only if $cors_origin is set
    add_header 'Access-Control-Allow-Origin' $cors_origin always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE, PATCH' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
    
    location / {
        # Handle preflight requests (OPTIONS)
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' $cors_origin always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE, PATCH' always;
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
        
        # Proxy configuration
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
        send_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 16k;
        proxy_busy_buffers_size 24k;
        proxy_buffers 64 4k;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/xerpex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 11. Configure SSL with Let's Encrypt

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Obtain and configure SSL certificates:

```bash
sudo certbot --nginx -d kebunsu-be-staging.tugugroup.co.id
```

Follow the prompts to complete the SSL configuration.

## 12. Firewall Configuration

Configure the firewall to allow HTTP, HTTPS, and SSH:

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

## 13. Maintenance and Monitoring

### Updating the Application

To update the application:

```bash
cd /opt/xerpex
source venv/bin/activate
git pull  # If using git
pip install -r requirements.txt  # If dependencies changed
alembic upgrade head  # If database schema changed
sudo supervisorctl restart xerpex
```

### Checking Logs

Application logs:

```bash
sudo tail -f /var/log/xerpex/out.log
sudo tail -f /var/log/xerpex/err.log
```

Nginx logs:

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

### 502 Bad Gateway

If you encounter a 502 Bad Gateway error:

1. Check if the application is running:
   ```bash
   sudo supervisorctl status xerpex
   ```

2. Check application logs:
   ```bash
   sudo tail -f /var/log/xerpex/err.log
   ```

3. Ensure the application is listening on the correct port:
   ```bash
   sudo netstat -tulpn | grep 8000
   ```

### Database Connection Issues

If the application can't connect to the database:

1. Verify MySQL is running:
   ```bash
   sudo systemctl status mysql
   ```

2. Check database credentials in the `.env` file.

3. Test database connection:
   ```bash
   mysql -u xerpex_user -p -h localhost xerpex_db
   ```

### MySQL Client Installation Issues

If you encounter errors related to `mysqlclient` installation like:

```
pkg-config: not found
Can not find valid pkg-config name.
Specify MYSQLCLIENT_CFLAGS and MYSQLCLIENT_LDFLAGS env vars manually
```

Try the following solutions:

1. Install additional dependencies:
   ```bash
   sudo apt install -y pkg-config python3-dev default-libmysqlclient-dev build-essential
   ```

2. If the issue persists, you can set the environment variables manually:
   ```bash
   export MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
   export MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient"
   pip install mysqlclient
   ```

3. Alternatively, you can try installing the binary wheel:
   ```bash
   pip install --only-binary :all: mysqlclient
   ```

### CORS Issues

If you encounter CORS issues:

1. Verify the CORS configuration in the Nginx config.
2. Ensure the `BACKEND_CORS_ORIGINS` in the `.env` file includes all necessary origins.
3. Restart Nginx after any configuration changes:
   ```bash
   sudo systemctl restart nginx
   ```

## Security Considerations

1. **Keep the server updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Use strong passwords** for all accounts.

3. **Restrict SSH access**:
   - Use key-based authentication
   - Disable password authentication
   - Consider changing the default SSH port

4. **Regularly backup the database**:
   ```bash
   mysqldump -u xerpex_user -p xerpex_db > backup_$(date +%Y%m%d).sql
   ```

5. **Monitor the server** for suspicious activities.