# Testing Database Connection Using Docker Compose

To test the database connection using Docker Compose, follow these steps:

## Prerequisites
- Docker and Docker Compose installed and running
- The application container built and running

## Steps to Test Database Connection

1. **Start the Docker containers** (if not already running):
   ```bash
   docker-compose up -d
   ```

2. **Execute the test script inside the container**:
   ```bash
   docker-compose exec kebunsu-api python test_db_connection.py
   ```
   
   This command runs the `test_db_connection.py` script inside the running API container.

3. **Expected output on success**:
   ```
   Testing connection to: mysql+mysqldb://xerpex_db:p7L5Tov236@127.0.0.1:3306/xerpex_db
   Connection successful!
   Result: (1,)
   ```

## Troubleshooting

If you encounter issues:

1. **Check if the container is running**:
   ```bash
   docker-compose ps
   ```

2. **Check container logs**:
   ```bash
   docker-compose logs api
   ```

3. **Verify MySQL is running and accessible**:
   ```bash
   docker-compose exec api ping -c 3 mysql
   ```
   
   If using host network mode, try:
   ```bash
   docker-compose exec api ping -c 3 127.0.0.1
   ```

4. **Verify environment variables inside the container**:
   ```bash
   docker-compose exec api env | grep MYSQL
   ```

## Notes for Production Environment

In a production environment, make sure:

1. The MySQL server is running and accessible from the application container
2. The database user has proper permissions
3. The database exists and is properly configured
4. Firewall rules allow connections to the MySQL port (3306 by default)

After testing, you can restart the application container to apply the configuration changes:
```bash
docker-compose restart api