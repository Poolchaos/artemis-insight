#!/bin/bash
# Artemis Insight Production Deployment Script
# This script deploys the entire stack using docker-compose

set -e

DEPLOY_DIR="/opt/artemis-insight"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=========================================="
echo "Artemis Insight Production Deployment"
echo "=========================================="
echo ""

# Create deployment directory if it doesn't exist
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "[1] Creating deployment directory..."
    sudo mkdir -p "$DEPLOY_DIR"
    sudo chown $USER:$USER "$DEPLOY_DIR"
fi

cd "$DEPLOY_DIR"

# Download docker-compose file from repository
echo "[2] Downloading latest docker-compose configuration..."
curl -sL https://raw.githubusercontent.com/Poolchaos/artemis-insight/main/docker-compose.prod.yml -o docker-compose.prod.yml

# Download monitoring configuration
echo "[3] Setting up monitoring configuration..."
mkdir -p monitoring/grafana/provisioning/datasources
curl -sL https://raw.githubusercontent.com/Poolchaos/artemis-insight/main/monitoring/prometheus.yml -o monitoring/prometheus.yml
curl -sL https://raw.githubusercontent.com/Poolchaos/artemis-insight/main/monitoring/grafana/provisioning/datasources/prometheus.yml -o monitoring/grafana/provisioning/datasources/prometheus.yml

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "[4] Creating .env file..."
    cat > .env << 'EOF'
# MongoDB
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=CHANGE_ME
MONGO_DATABASE=artemis_insight

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=CHANGE_ME
MINIO_BUCKET=artemis-insight

# JWT
JWT_SECRET_KEY=CHANGE_ME

# OpenAI
OPENAI_API_KEY=CHANGE_ME
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Cost Management
MONTHLY_BUDGET_ZAR=1000

# Docker Images
API_IMAGE=ghcr.io/poolchaos/artemis-insight-backend:latest
WEB_IMAGE=ghcr.io/poolchaos/artemis-insight-frontend:latest

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=CHANGE_ME
EOF
    echo "⚠️  WARNING: Update .env file with secure passwords!"
    echo "⚠️  Edit: $DEPLOY_DIR/.env"
else
    echo "[4] Using existing .env file"
fi

# Deploy infrastructure services first
echo "[5] Deploying infrastructure services..."
docker-compose -f $COMPOSE_FILE up -d mongodb redis minio

echo "[6] Waiting for infrastructure to be ready (30 seconds)..."
sleep 30

# Deploy monitoring stack
echo "[7] Deploying monitoring stack..."
docker-compose -f $COMPOSE_FILE up -d prometheus grafana cadvisor

# Deploy application services
echo "[8] Deploying application services..."
docker-compose -f $COMPOSE_FILE up -d backend celery_worker celery_beat frontend

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Services Status:"
docker-compose -f $COMPOSE_FILE ps
echo ""
echo "Access URLs:"
echo "  Frontend:    http://localhost:3003"
echo "  Backend API: http://localhost:8002"
echo "  Grafana:     http://localhost:3100"
echo "  MinIO:       http://localhost:9003"
echo ""
echo "Logs: docker-compose -f $DEPLOY_DIR/$COMPOSE_FILE logs -f"
echo "Stop: docker-compose -f $DEPLOY_DIR/$COMPOSE_FILE down"
echo ""
