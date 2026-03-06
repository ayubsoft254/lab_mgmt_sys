.PHONY: build up down restart logs shell shell-db shell-redis migrate collectstatic createsuperuser help

# Default target
help:
	@echo "Lab Management System - Docker Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  build           Build all Docker images"
	@echo "  up              Start all services in detached mode"
	@echo "  down            Stop and remove all containers"
	@echo "  restart         Restart all services"
	@echo "  logs            Follow logs for all services"
	@echo "  logs-web        Follow logs for the web service only"
	@echo ""
	@echo "  shell           Open a bash shell inside the web container"
	@echo "  shell-db        Open a psql shell inside the database container"
	@echo "  shell-redis     Open a redis-cli shell inside the Redis container"
	@echo ""
	@echo "  migrate         Run Django database migrations"
	@echo "  collectstatic   Collect static files"
	@echo "  createsuperuser Create a Django superuser"

## Docker lifecycle

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

## Logs

logs:
	docker compose logs -f

logs-web:
	docker compose logs -f web

## Container shells

shell:
	docker compose exec web /bin/bash

shell-db:
	docker compose exec db psql -U $${DB_USER:-labuser} $${DB_NAME:-lab_mgmt}

shell-redis:
	docker compose exec redis redis-cli

## Django management

migrate:
	docker compose exec web python manage.py migrate

collectstatic:
	docker compose exec web python manage.py collectstatic --noinput

createsuperuser:
	docker compose exec web python manage.py createsuperuser
