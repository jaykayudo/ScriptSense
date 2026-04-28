# List all available commands
default:
    @just --list

# Install all dependencies (frontend + Python workspace)
install:
    cd frontend && npm install
    uv sync

# Start all services in dev mode
dev:
    bash start.sh

# Build Docker images
build:
    docker-compose build

# Start all Docker containers
up:
    docker-compose up

# Stop all Docker containers
down:
    docker-compose down

# Run model training
train:
    uv run python -m model.train

# Remove build artifacts and caches
clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -name "*.pyc" -delete
    cd frontend && rm -rf dist

# copy the environmental variables
env_copy:
	cp frontend/.env.example frontend/.env
	cp backend/.env.example backend/.env