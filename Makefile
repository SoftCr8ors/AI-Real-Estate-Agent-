.PHONY: help install dev test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make dev        - Start all services (Docker + Backend + Frontend)"
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean up containers and volumes"

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Waiting for database..."
	timeout /t 5
	@echo "Running migrations..."
	cd backend && python -m alembic upgrade head
	@echo "Starting backend..."
	start cmd /k "cd backend && uvicorn app.main:app --reload"
	@echo "Starting frontend..."
	start cmd /k "cd frontend && npm run dev"

test:
	cd backend && pytest
	cd frontend && npm run build

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .

clean:
	docker-compose down -v