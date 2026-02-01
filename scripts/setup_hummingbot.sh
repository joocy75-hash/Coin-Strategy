#!/bin/bash

# ============================================================
# 🚀 Hummingbot v2.11.0 (Latest) Complete Setup Script
# ============================================================
# Last Updated: 2026-01-19
# This script sets up Hummingbot with Gateway and Dashboard
# ============================================================

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🤖 Hummingbot v2.11.0 Complete Installation               ║"
echo "║     Market Making + Arbitrage + DEX Trading                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HUMMINGBOT_DIR="$PROJECT_ROOT/hummingbot"

# ==========================================
# Step 1: Check Docker
# ==========================================
echo "📋 Step 1/5: Checking Docker..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker command not found."
    echo "   Attempting to start Docker Desktop..."
    
    if [ -d "/Applications/Docker.app" ]; then
        open -a Docker
        echo "⏳ Waiting for Docker Desktop to start (30 seconds)..."
        sleep 30
    else
        echo "❌ Docker Desktop not installed!"
        echo "   Please install from: https://www.docker.com/products/docker-desktop/"
        exit 1
    fi
fi

# Wait for Docker daemon
echo "⏳ Waiting for Docker daemon..."
RETRY=0
MAX_RETRY=30
while ! docker info &> /dev/null; do
    RETRY=$((RETRY+1))
    if [ $RETRY -gt $MAX_RETRY ]; then
        echo "❌ Docker daemon failed to start. Please start Docker Desktop manually."
        exit 1
    fi
    echo "   Retrying... ($RETRY/$MAX_RETRY)"
    sleep 2
done
echo "✅ Docker is running!"
echo ""

# ==========================================
# Step 2: Create Directory Structure
# ==========================================
echo "📁 Step 2/5: Creating directory structure..."

mkdir -p "$HUMMINGBOT_DIR/conf"
mkdir -p "$HUMMINGBOT_DIR/logs"
mkdir -p "$HUMMINGBOT_DIR/data"
mkdir -p "$HUMMINGBOT_DIR/scripts"
mkdir -p "$HUMMINGBOT_DIR/certs"
mkdir -p "$HUMMINGBOT_DIR/gateway-conf"
mkdir -p "$HUMMINGBOT_DIR/gateway-logs"

echo "✅ Directories created!"
echo ""

# ==========================================
# Step 3: Pull Latest Images
# ==========================================
echo "📦 Step 3/5: Pulling latest Hummingbot images..."
echo "   This may take a few minutes..."
echo ""

docker pull hummingbot/hummingbot:latest
echo "✅ Hummingbot core pulled!"

docker pull hummingbot/gateway:latest
echo "✅ Gateway (DEX middleware) pulled!"

docker pull hummingbot/dashboard:latest || echo "⚠️  Dashboard image not available (optional)"

echo ""
echo "✅ All images pulled successfully!"
echo ""

# ==========================================
# Step 4: Create Docker Compose File
# ==========================================
echo "📝 Step 4/5: Generating docker-compose.yml..."

cat << 'EOF' > "$HUMMINGBOT_DIR/docker-compose.yml"
version: "3.9"

services:
  hummingbot:
    image: hummingbot/hummingbot:latest
    container_name: hummingbot
    restart: unless-stopped
    volumes:
      - ./conf:/home/hummingbot/conf
      - ./logs:/home/hummingbot/logs
      - ./data:/home/hummingbot/data
      - ./scripts:/home/hummingbot/scripts
      - ./certs:/home/hummingbot/certs
    stdin_open: true
    tty: true
    environment:
      - CONFIG_PASSWORD=${HUMMINGBOT_PASSWORD:-admin123}
    networks:
      - hummingbot-network

  gateway:
    image: hummingbot/gateway:latest
    container_name: hummingbot-gateway
    restart: unless-stopped
    ports:
      - "15888:15888"
    volumes:
      - ./gateway-conf:/home/gateway/conf
      - ./gateway-logs:/home/gateway/logs
      - ./certs:/home/gateway/certs
    environment:
      - GATEWAY_PASSPHRASE=${GATEWAY_PASSPHRASE:-admin}
      - DEV=true
    networks:
      - hummingbot-network
    depends_on:
      - hummingbot

networks:
  hummingbot-network:
    driver: bridge
EOF

echo "✅ docker-compose.yml created!"
echo ""

# ==========================================
# Step 5: Start Services
# ==========================================
echo "🚀 Step 5/5: Starting Hummingbot services..."

cd "$HUMMINGBOT_DIR"
docker compose up -d

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Hummingbot v2.11.0 Installation Complete!              ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  📍 Service Ports:                                         ║"
echo "║     • Hummingbot CLI: docker attach hummingbot             ║"
echo "║     • Gateway API:    http://localhost:15888               ║"
echo "║     • Dashboard UI:   http://localhost:8501 (if enabled)   ║"
echo "║                                                            ║"
echo "║  🛠️  Useful Commands:                                      ║"
echo "║     • Attach to bot: docker attach hummingbot              ║"
echo "║     • View logs:     docker logs -f hummingbot             ║"
echo "║     • Stop all:      docker compose down                   ║"
echo "║     • Restart:       docker compose restart                ║"
echo "║                                                            ║"
echo "║  📚 Documentation: https://hummingbot.org/installation/    ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "💡 To connect to Hummingbot CLI, run:"
echo "   docker attach hummingbot"
echo ""
echo "   (To detach without stopping: Ctrl+P, then Ctrl+Q)"
