.PHONY: help install run test lint clean docker-build docker-run docker-stop

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make run         - Run the bot locally"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linting"
	@echo "  make clean       - Clean up cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run  - Run bot in Docker"
	@echo "  make docker-stop - Stop Docker container"

# Install dependencies
install:
	pip install -r requirements.txt

# Run the bot locally
run:
	python -m src.app

# Run tests
test:
	python -m pytest tests/ -v

# Run linting (requires flake8 to be installed)
lint:
	@echo "Running flake8..."
	@pip install flake8 --quiet
	@flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

# Docker commands
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# Development setup
dev-setup: install
	@echo "Setting up development environment..."
	@cp .env.example .env
	@echo "Please edit .env file with your configuration"

# Production run with gunicorn
prod:
	gunicorn -w 4 -b 0.0.0.0:${FLASK_PORT:-3000} --timeout 120 src.app:create_app