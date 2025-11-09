#!/bin/bash
# ============================================================================
# Database Security Setup Script
# This script sets up the secure configuration for your Youcef project
# ============================================================================

set -e

echo "🔒 Youcef Database Security Setup"
echo "=================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and set strong values for:"
    echo "   - DB_PASSWORD (at least 20 chars with special chars)"
    echo "   - SECRET_KEY"
    echo "   - CORS_ORIGINS"
    echo "   - VITE_API_URL"
    echo ""
    read -p "Press Enter once you've updated .env file..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "📦 Stopping existing containers..."
docker-compose down || true

echo ""
echo "🗑️  Removing old database volume (to apply new security rules)..."
docker volume rm youcef_postgres_data || true

echo ""
echo "🚀 Starting containers with new security configuration..."
docker-compose up -d

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📊 Verification:"
echo "   Backend: http://localhost:8001"
echo "   Frontend: http://localhost:3000"
echo ""
echo "🔍 To verify database security, run:"
echo "   docker-compose ps"
echo "   # Should show ports 3000:3000 and 8001:8001, but NOT 5432"
echo ""
echo "📖 For more information, see DATABASE_SECURITY.md"
