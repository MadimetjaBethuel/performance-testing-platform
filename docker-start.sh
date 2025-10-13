#!/bin/bash

# Performance Testing Platform - Docker Startup Script
# This script helps you quickly start the dockerized performance testing platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Performance Testing Platform - Docker Setup${NC}"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file with your actual configuration values.${NC}"
        echo -e "${YELLOW}Opening .env file for editing...${NC}"
        ${EDITOR:-nano} .env
    else
        echo -e "${RED}Error: .env.example file not found.${NC}"
        exit 1
    fi
fi

# Check if input data exists
if [ ! -f data/input.json ]; then
    echo -e "${YELLOW}Warning: data/input.json not found. Creating sample file...${NC}"
    mkdir -p data
    cat > data/input.json << EOF
{
  "urls": [
    {"url": "https://httpbin.org/delay/1", "name": "HTTPBin Delay Test"},
    {"url": "https://httpbin.org/status/200", "name": "HTTPBin Status Test"}
  ]
}
EOF
    echo -e "${GREEN}Sample input.json created in data/ directory.${NC}"
fi

# Function to display menu
show_menu() {
    echo ""
    echo "Please select an option:"
    echo "1) Build and run the application"
    echo "2) Run in development mode (with shell access)"
    echo "3) View logs"
    echo "4) Stop all services"
    echo "5) Clean up (remove containers and images)"
    echo "6) Exit"
    echo ""
}

# Main menu loop
while true; do
    show_menu
    read -p "Enter your choice [1-6]: " choice
    
    case $choice in
        1)
            echo -e "${GREEN}Building and starting the performance testing platform...${NC}"
            docker-compose up --build -d
            echo -e "${GREEN}Application started! Use option 3 to view logs.${NC}"
            ;;
        2)
            echo -e "${GREEN}Starting development environment...${NC}"
            docker-compose --profile dev up -d performance-dev
            echo -e "${GREEN}Development container started. Access with:${NC}"
            echo -e "${YELLOW}docker-compose exec performance-dev bash${NC}"
            ;;
        3)
            echo -e "${GREEN}Showing logs (Ctrl+C to exit):${NC}"
            docker-compose logs -f
            ;;
        4)
            echo -e "${YELLOW}Stopping all services...${NC}"
            docker-compose down
            echo -e "${GREEN}All services stopped.${NC}"
            ;;
        5)
            echo -e "${YELLOW}Cleaning up containers and images...${NC}"
            docker-compose down --rmi all --volumes
            echo -e "${GREEN}Cleanup completed.${NC}"
            ;;
        6)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            ;;
    esac
done