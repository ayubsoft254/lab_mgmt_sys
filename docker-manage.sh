#!/usr/bin/env bash

# Lab Management System - Docker Management Script
# Usage: ./docker-manage.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
${BLUE}Lab Management System - Docker Management${NC}

${YELLOW}Usage:${NC}
  ./docker-manage.sh [command] [options]

${YELLOW}Commands:${NC}
  up                 Start all services
  down               Stop all services
  logs               Display logs from all services
  logs [service]     Display logs from specific service (web, db, redis, celery_worker, celery_beat)
  restart            Restart all services
  restart [service]  Restart specific service
  shell [service]    Open shell in container (default: web)
  exec [service] [cmd]  Execute command in container
  migrate            Run database migrations
  createsuperuser    Create admin user
  backup             Backup database to backup.sql
  restore            Restore database from backup.sql
  clean              Remove containers and volumes (WARNING: deletes data!)
  ps                 Show container status
  top [service]      Show resource usage (default: web)
  build              Build Docker images
  status             Show application status
  health             Check service health
  help               Show this help message

${YELLOW}Examples:${NC}
  ./docker-manage.sh up
  ./docker-manage.sh logs web
  ./docker-manage.sh exec web python manage.py shell
  ./docker-manage.sh createsuperuser
  ./docker-manage.sh backup

EOF
}

# Check if Docker and Docker Compose are installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi
}

# Start services
start_services() {
    echo -e "${BLUE}Starting services...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Services started${NC}"
    sleep 5
    show_status
}

# Stop services
stop_services() {
    echo -e "${BLUE}Stopping services...${NC}"
    docker-compose down
    echo -e "${GREEN}Services stopped${NC}"
}

# Show logs
show_logs() {
    local service=${1:-}
    if [ -z "$service" ]; then
        echo -e "${BLUE}Showing logs from all services...${NC}"
        docker-compose logs -f
    else
        echo -e "${BLUE}Showing logs from ${service}...${NC}"
        docker-compose logs -f "$service"
    fi
}

# Restart services
restart_services() {
    local service=${1:-}
    if [ -z "$service" ]; then
        echo -e "${BLUE}Restarting all services...${NC}"
        docker-compose restart
    else
        echo -e "${BLUE}Restarting ${service}...${NC}"
        docker-compose restart "$service"
    fi
    sleep 3
    show_status
}

# Open shell
open_shell() {
    local service=${1:-web}
    echo -e "${BLUE}Opening shell in ${service}...${NC}"
    docker-compose exec "$service" /bin/bash
}

# Execute command
execute_command() {
    local service=$1
    shift
    local cmd="$@"
    echo -e "${BLUE}Executing: $cmd${NC}"
    docker-compose exec "$service" $cmd
}

# Run migrations
run_migrations() {
    echo -e "${BLUE}Running migrations...${NC}"
    docker-compose exec web python manage.py migrate
    echo -e "${GREEN}Migrations completed${NC}"
}

# Create superuser
create_superuser() {
    echo -e "${BLUE}Creating superuser...${NC}"
    docker-compose exec web python manage.py createsuperuser
    echo -e "${GREEN}Superuser created${NC}"
}

# Backup database
backup_db() {
    echo -e "${BLUE}Backing up database...${NC}"
    docker-compose exec db pg_dump -U labuser lab_mgmt > backup.sql
    echo -e "${GREEN}Database backed up to backup.sql${NC}"
}

# Restore database
restore_db() {
    if [ ! -f backup.sql ]; then
        echo -e "${RED}Error: backup.sql not found${NC}"
        exit 1
    fi
    echo -e "${YELLOW}WARNING: This will overwrite the current database${NC}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Restoring database...${NC}"
        docker-compose exec -T db psql -U labuser lab_mgmt < backup.sql
        echo -e "${GREEN}Database restored${NC}"
    fi
}

# Clean up
cleanup() {
    echo -e "${YELLOW}WARNING: This will remove all containers and volumes, deleting all data${NC}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Cleaning up...${NC}"
        docker-compose down -v
        echo -e "${GREEN}Cleanup completed${NC}"
    fi
}

# Show container status
show_ps() {
    echo -e "${BLUE}Container Status:${NC}"
    docker-compose ps
}

# Show resource usage
show_top() {
    local service=${1:-web}
    echo -e "${BLUE}Resource Usage - ${service}:${NC}"
    docker stats --no-stream "lab_mgmt_${service}" 2>/dev/null || echo -e "${RED}Container not running${NC}"
}

# Build images
build_images() {
    echo -e "${BLUE}Building Docker images...${NC}"
    docker-compose build
    echo -e "${GREEN}Build completed${NC}"
}

# Show status summary
show_status() {
    echo -e "\n${BLUE}=== Application Status ===${NC}"
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Services running${NC}"
    else
        echo -e "${RED}✗ Services not running${NC}"
        return
    fi
    
    # Check database
    if docker-compose exec db pg_isready -U labuser > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Database ready${NC}"
    else
        echo -e "${RED}✗ Database not ready${NC}"
    fi
    
    # Check Redis
    if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis ready${NC}"
    else
        echo -e "${RED}✗ Redis not ready${NC}"
    fi
    
    # Check web server
    if docker-compose exec web curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Web server ready${NC}"
    else
        echo -e "${YELLOW}⚠ Web server starting...${NC}"
    fi
    
    echo -e "\n${BLUE}=== Application URLs ===${NC}"
    echo -e "Application: ${GREEN}http://localhost:8000${NC}"
    echo -e "Admin: ${GREEN}http://localhost:8000/admin${NC}"
    echo -e "\n${BLUE}View logs with: ${GREEN}./docker-manage.sh logs${NC}\n"
}

# Health check
health_check() {
    echo -e "${BLUE}=== Health Check ===${NC}"
    
    local all_healthy=true
    
    # Check PostgreSQL
    echo -n "PostgreSQL: "
    if docker-compose exec db pg_isready -U labuser > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        all_healthy=false
    fi
    
    # Check Redis
    echo -n "Redis: "
    if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        all_healthy=false
    fi
    
    # Check Web
    echo -n "Web Server: "
    if docker-compose exec web curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        all_healthy=false
    fi
    
    # Check Celery
    echo -n "Celery Worker: "
    if docker-compose logs celery_worker 2>/dev/null | grep -q "ready to accept tasks"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        echo -e "\n${GREEN}All services are healthy${NC}"
        return 0
    else
        echo -e "\n${RED}Some services are unhealthy${NC}"
        return 1
    fi
}

# Main
check_docker

case "${1:-help}" in
    up)
        start_services
        ;;
    down)
        stop_services
        ;;
    logs)
        show_logs "$2"
        ;;
    restart)
        restart_services "$2"
        ;;
    shell)
        open_shell "$2"
        ;;
    exec)
        execute_command "$2" "${@:3}"
        ;;
    migrate)
        run_migrations
        ;;
    createsuperuser)
        create_superuser
        ;;
    backup)
        backup_db
        ;;
    restore)
        restore_db
        ;;
    clean)
        cleanup
        ;;
    ps)
        show_ps
        ;;
    top)
        show_top "$2"
        ;;
    build)
        build_images
        ;;
    status)
        show_status
        ;;
    health)
        health_check
        ;;
    help)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
