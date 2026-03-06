.PHONY: build up down restart login migrate collectstatic logs

# Build the Docker images
build:
	docker compose build

# Start all containers in detached mode
up:
	docker compose up -d

# Stop and remove all containers
down:
	docker compose down

# Restart all containers
restart:
	docker compose restart

# Login (exec) into the web container
login:
	docker exec -it lab_mgmt_web /bin/bash

# Run Django database migrations inside the container
migrate:
	docker compose exec web python manage.py migrate

# Collect static files inside the container
collectstatic:
	docker compose exec web python manage.py collectstatic --noinput

# Tail logs for all containers
logs:
	docker compose logs -f
