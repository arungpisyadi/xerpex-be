#!/bin/bash

cd be-staging
git pull
docker-compose down --rmi all --volumes
docker-compose -f docker-compose-staging.yml up --build --force-recreate -d
# docker compose exec kebunsu-api-staging bash -c "python test_db_connection.py"
cd ~
