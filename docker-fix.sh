#!/bin/bash

echo "============================================================================"
echo "  🚨 DOCKER FIX SCRIPT - Youcef Project"
echo "============================================================================"
echo

echo "[1/5] Stopping all containers..."
docker-compose down

echo
echo "[2/5] Removing failed containers..."
docker-compose rm -f

echo
echo "[3/5] Cleaning up Docker system..."
docker system prune -f

echo
echo "[4/5] Building fresh images..."
docker-compose build --no-cache

echo
echo "[5/5] Starting services..."
docker-compose up -d

echo
echo "============================================================================"
echo "  ✅ FIX COMPLETE!"
echo "============================================================================"
echo
echo "Checking status..."
docker-compose ps

echo
echo "📊 To view logs:"
echo "  docker-compose logs -f"
echo
echo "🌐 Access your app:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8001/docs"
echo
