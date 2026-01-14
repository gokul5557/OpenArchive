#!/bin/bash

# OpenArchive Startup Script
# Starts: Docker Infrastructure, Core API, Sidecar Agent, and Web UI.

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting OpenArchive Stack...${NC}"

# 1. Start Docker Infrastructure
echo -e "${GREEN}[1/4] Starting Infrastructure (MinIO, Meilisearch, Postgres)...${NC}"
docker-compose up -d
sleep 5 # Wait for DB to be ready

# Export Environment Variables for local processes
export DATABASE_URL="postgresql://admin:password@127.0.0.1:5432/openarchive"
export MINIO_ENDPOINT="http://127.0.0.1:9000"
export MINIO_ROOT_USER="admin"
export MINIO_ROOT_PASSWORD="password"
export MEILI_HTTP_ADDR="http://127.0.0.1:7700"
export MEILI_MASTER_KEY="masterKey"
export CORE_API_KEY="secret_shared_key"
export OPENARCHIVE_MASTER_KEY="local-dev-key"
export CORE_API_URL="http://127.0.0.1:8000/api/v1/sync"
export PYTHONHTTPSVERIFY=0
export AGENT_ORG_ID="13" # Sagasoft Org ID

# 2. Start Core API
echo -e "${GREEN}[2/4] Starting Core API (Port 8000)...${NC}"
# Kill existing if any
fuser -k 8000/tcp > /dev/null 2>&1 || true
cd core
nohup ../.venv/bin/python -m uvicorn main:app --port 8000 --host 0.0.0.0 > core_service.log 2>&1 &
echo "Core API running in background (pid $!). Logs: core/core_service.log"
cd ..

# 3. Start Sidecar Agent
echo -e "${GREEN}[3/4] Starting Sidecar SMTP Agent (Port 2525)...${NC}"
fuser -k 2525/tcp > /dev/null 2>&1 || true
cd sidecar
nohup ../.venv/bin/python agent.py > agent_service.log 2>&1 &
echo "SMTP Agent running in background (pid $!). Logs: sidecar/agent_service.log"
# Start Sync Worker
nohup ../.venv/bin/python sync.py > sync_service.log 2>&1 &
echo "Sync Worker running in background (pid $!). Logs: sidecar/sync_service.log"
cd ..

# 4. Start Web UI
echo -e "${GREEN}[4/4] Starting Web UI (Port 3000)...${NC}"
cd ui
# Check if build is needed, but assuming user wants to just RUN
nohup npm run dev > ui_service.log 2>&1 &
echo "Web UI running in background (pid $!). Logs: ui/ui_service.log"
cd ..

echo -e "${BLUE}==============================================${NC}"
echo -e "${GREEN}OpenArchive is fully operational!${NC}"
echo -e "   - UI:       http://localhost:3000"
echo -e "   - API:      http://localhost:8000/docs"
echo -e "   - SMTP:     localhost:2525"
echo -e "${BLUE}==============================================${NC}"
