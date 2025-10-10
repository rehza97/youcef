#!/bin/bash
# ============================================================================
# Youcef Project - Docker Startup Script (Linux/Mac)
# ============================================================================

set -e

echo ""
echo "============================================================================"
echo "  YOUCEF PROJECT - DOCKER STARTUP"
echo "============================================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running!"
    echo ""
    echo "Please start Docker and try again."
    echo ""
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo "❌ ERROR: docker-compose not found!"
    echo ""
    echo "Please install Docker Compose and try again."
    echo ""
    exit 1
fi

echo "✅ docker-compose found"
echo ""

echo "============================================================================"
echo "  STARTUP OPTIONS"
echo "============================================================================"
echo ""
echo "  1. Fresh start (build + start)"
echo "  2. Quick start (no rebuild)"
echo "  3. Start with auto-update from git"
echo "  4. Stop all containers"
echo "  5. Stop and remove all (clean slate)"
echo "  6. View logs"
echo "  7. Exit"
echo ""
read -p "Enter your choice (1-7): " choice

case $choice in
    1)
        echo ""
        echo "🔨 Building and starting containers..."
        echo ""
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    2)
        echo ""
        echo "🚀 Starting containers (no rebuild)..."
        echo ""
        docker-compose up -d
        ;;
    3)
        echo ""
        echo "🔄 Starting with auto-update from git enabled..."
        echo ""
        export AUTO_GIT_UPDATE=true
        docker-compose down
        docker-compose build
        docker-compose up -d
        ;;
    4)
        echo ""
        echo "⏸️  Stopping all containers..."
        echo ""
        docker-compose stop
        echo ""
        echo "✅ All containers stopped"
        echo ""
        exit 0
        ;;
    5)
        echo ""
        echo "🗑️  Stopping and removing all containers, networks, and volumes..."
        echo ""
        docker-compose down -v
        echo ""
        echo "✅ Clean slate complete"
        echo ""
        exit 0
        ;;
    6)
        echo ""
        echo "============================================================================"
        echo "  CONTAINER LOGS"
        echo "============================================================================"
        echo ""
        docker-compose logs --tail=50 --follow
        exit 0
        ;;
    7)
        exit 0
        ;;
    *)
        echo "❌ Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "============================================================================"
echo "  WAITING FOR SERVICES TO START"
echo "============================================================================"
echo ""
sleep 10

# Check container status
docker-compose ps

echo ""
echo "============================================================================"
echo "  YOUCEF PROJECT - RUNNING"
echo "============================================================================"
echo ""
echo "  PostgreSQL:  localhost:5432"
echo "  Backend:     http://localhost:8001"
echo "  API Docs:    http://localhost:8001/docs"
echo "  Frontend:    http://localhost:3000"
echo ""
echo "============================================================================"
echo "  USEFUL COMMANDS"
echo "============================================================================"
echo ""
echo "  View logs:           docker-compose logs -f"
echo "  Stop all:            docker-compose stop"
echo "  Restart all:         docker-compose restart"
echo "  Remove all:          docker-compose down -v"
echo ""
echo "  View backend logs:   docker-compose logs -f backend"
echo "  View frontend logs:  docker-compose logs -f frontend"
echo "  View database logs:  docker-compose logs -f postgres"
echo ""
echo "============================================================================"
echo ""

