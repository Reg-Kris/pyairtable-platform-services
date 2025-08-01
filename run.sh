#!/bin/bash

# Platform Services Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Platform Services (Auth + Analytics)${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Create data directory
mkdir -p data
mkdir -p logs

# Set environment variables
export DATABASE_URL="sqlite:///./data/platform_services.db"
export ANALYTICS_DB_PATH="./data/analytics.db"
export SERVICE_HOST="0.0.0.0"
export SERVICE_PORT="8007"

# Check if .env file exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Loading environment variables from .env...${NC}"
    export $(cat .env | xargs)
else
    echo -e "${YELLOW}No .env file found. Using defaults. Copy .env.example to .env for custom configuration.${NC}"
fi

# Run the application
echo -e "${GREEN}Starting Platform Services on port ${SERVICE_PORT}...${NC}"
echo -e "${GREEN}Auth endpoints: http://localhost:${SERVICE_PORT}/auth/*${NC}"
echo -e "${GREEN}Analytics endpoints: http://localhost:${SERVICE_PORT}/analytics/*${NC}"
echo -e "${GREEN}Health check: http://localhost:${SERVICE_PORT}/health${NC}"
echo -e "${GREEN}API docs: http://localhost:${SERVICE_PORT}/docs${NC}"

python main.py