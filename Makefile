.PHONY: install dev build up down train clean

install:
	cd frontend && npm install
	uv sync

dev:
	@bash start.sh

build:
	docker-compose build

up:
	docker-compose up

down:
	docker-compose down

train:
	uv run python -m model.train

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	cd frontend && rm -rf dist

env_copy:
	cp frontend/.env.example frontend/.env
	cp backend/.env.example backend/.env