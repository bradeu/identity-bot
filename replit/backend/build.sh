#!/bin/bash

# Multilingual RAG Backend Build Script
# Usage: ./build.sh [environment] [options]
# Environments: dev, test, prod
# Options: --rebuild, --logs, --test, --clean

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-dev}
REBUILD=false
SHOW_LOGS=true
RUN_TESTS=false
CLEAN=false

# Parse command line arguments
for arg in "$@"; do
  case $arg in
    --rebuild)
      REBUILD=true
      shift
      ;;
    --no-logs)
      SHOW_LOGS=false
      shift
      ;;
    --test)
      RUN_TESTS=true
      shift
      ;;
    --clean)
      CLEAN=true
      shift
      ;;
    --help)
      echo "Usage: $0 [environment] [options]"
      echo "Environments: dev, test, prod"
      echo "Options:"
      echo "  --rebuild    Force rebuild of containers"
      echo "  --no-logs    Don't show container logs after startup"
      echo "  --test       Run tests after build"
      echo "  --clean      Clean up containers and volumes before build"
      echo "  --help       Show this help message"
      exit 0
      ;;
  esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|test|prod)$ ]]; then
  echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'. Use: dev, test, or prod${NC}"
  exit 1
fi

echo -e "${BLUE}🚀 Building Multilingual RAG Backend${NC}"
echo -e "${BLUE}Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo "----------------------------------------"

# Set compose file based on environment
COMPOSE_FILE="docker-compose.yml"
if [[ "$ENVIRONMENT" == "prod" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
elif [[ "$ENVIRONMENT" == "test" ]]; then
  COMPOSE_FILE="docker-compose.test.yml"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}❌ Error: Docker is not running. Please start Docker and try again.${NC}"
  exit 1
fi

# Check if required files exist
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo -e "${YELLOW}⚠️  $COMPOSE_FILE not found, using docker-compose.yml${NC}"
  COMPOSE_FILE="docker-compose.yml"
fi

if [[ ! -f ".env" && "$ENVIRONMENT" != "test" ]]; then
  echo -e "${YELLOW}⚠️  Warning: .env file not found. Creating from .env.example...${NC}"
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo -e "${YELLOW}Please update .env with your configuration${NC}"
  else
    echo -e "${YELLOW}No .env.example found. Please create .env file manually.${NC}"
  fi
fi

# Clean up if requested
if [[ "$CLEAN" == true ]]; then
  echo -e "${YELLOW}🧹 Cleaning up containers and volumes...${NC}"
  docker-compose -f "$COMPOSE_FILE" down --volumes --remove-orphans || true
  docker system prune -f
fi

# Build arguments
BUILD_ARGS="--build"
if [[ "$REBUILD" == true ]]; then
  BUILD_ARGS="$BUILD_ARGS --force-recreate"
fi

echo -e "${GREEN}🔨 Building and starting containers with docker-compose...${NC}"

# Build and start services
if [[ "$ENVIRONMENT" == "test" ]]; then
  echo -e "${BLUE}Building test environment...${NC}"
  docker-compose -f "$COMPOSE_FILE" build
  echo -e "${BLUE}Running tests...${NC}"
  docker-compose -f "$COMPOSE_FILE" run --rm app pytest tests/ -v --no-cov || true
else
  docker-compose -f "$COMPOSE_FILE" up $BUILD_ARGS -d
fi

# Wait for services to be ready (only for dev/prod)
if [[ "$ENVIRONMENT" != "test" ]]; then
  echo -e "${BLUE}⏳ Waiting for API to be ready...${NC}"
  
  # Wait for API to be ready
  for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health/ping > /dev/null 2>&1; then
      echo -e "${GREEN}✅ API is ready!${NC}"
      break
    fi
    if [[ $i -eq 30 ]]; then
      echo -e "${YELLOW}⚠️  API took longer than expected to start${NC}"
      break
    fi
    sleep 1
  done

  echo -e "${GREEN}🎉 Container started successfully!${NC}"
  echo -e "${BLUE}📍 API is accessible at: ${GREEN}http://localhost:8000${NC}"
  echo -e "${BLUE}📖 API Docs available at: ${GREEN}http://localhost:8000/docs${NC}"
  echo -e "${BLUE}🏥 Health Check: ${GREEN}http://localhost:8000/api/v1/health/ping${NC}"
  echo ""

  # Run tests if requested
  if [[ "$RUN_TESTS" == true ]]; then
    echo -e "${BLUE}🧪 Running tests...${NC}"
    docker-compose -f "$COMPOSE_FILE" exec app pytest tests/ -v --no-cov || true
  fi

  # Print logs
  if [[ "$SHOW_LOGS" == true ]]; then
    echo -e "${BLUE}📋 Showing logs (Ctrl+C to exit):${NC}"
    docker-compose -f "$COMPOSE_FILE" logs -f
  else
    echo ""
    echo -e "${BLUE}💡 Useful commands:${NC}"
    echo -e "  View logs:     docker-compose logs -f"
    echo -e "  Stop services: docker-compose down"
    echo -e "  Run tests:     docker-compose exec app pytest tests/"
    echo -e "  Shell access:  docker-compose exec app bash"
  fi
fi