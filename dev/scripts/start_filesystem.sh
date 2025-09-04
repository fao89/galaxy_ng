#!/bin/bash
# Start the filesystem-based galaxy_ng development environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/dev/compose/standalone-fs.yaml"

echo "Starting Galaxy NG Filesystem Development Environment"
echo "=============================================="
echo "Project root: $PROJECT_ROOT"
echo "Compose file: $COMPOSE_FILE"
echo ""

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Use docker compose or docker-compose based on availability
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Stop any existing containers
echo "Stopping any existing containers..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" down

# Build and start services
echo "Building and starting services..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up --build -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Show status
echo ""
echo "Service Status:"
echo "==============="
$DOCKER_COMPOSE -f "$COMPOSE_FILE" ps

echo ""
echo "Galaxy NG Filesystem Development Environment Ready!"
echo "=================================================="
echo ""
echo "Services:"
echo "  API Server:     http://localhost:5001/api/galaxy/"
echo "  Content Server: http://localhost:5678/"
echo "  PostgreSQL:     localhost:5433"
echo ""
echo "Credentials:"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "Useful commands:"
echo "  View logs:           $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f [service]"
echo "  Shell access:        $DOCKER_COMPOSE -f $COMPOSE_FILE exec [service] /bin/bash"
echo "  Django management:   $DOCKER_COMPOSE -f $COMPOSE_FILE exec manager python /src/manage.py [command]"
echo "  Monitor tasks:       $DOCKER_COMPOSE -f $COMPOSE_FILE exec manager python /src/manage.py list_tasks --watch"
echo "  Validate collections: $DOCKER_COMPOSE -f $COMPOSE_FILE exec manager python /src/manage.py validate_collections"
echo "  Stop environment:    $DOCKER_COMPOSE -f $COMPOSE_FILE down"
echo ""
echo "Content is stored in Docker volumes:"
echo "  Collections: galaxy_content_data"
echo "  Tasks:       galaxy_task_data"
echo "  Database:    galaxy_pg_data"