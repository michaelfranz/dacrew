.PHONY: help install test lint format clean build docker-build docker-run deploy aws-deploy

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run tests
	pytest tests/ -v

lint: ## Run linting checks
	black --check dacrew/ tests/
	isort --check-only dacrew/ tests/
	mypy dacrew/

format: ## Format code
	black dacrew/ tests/
	isort dacrew/ tests/

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf embeddings/
	rm -rf logs/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

build: ## Build the application
	python setup.py build

docker-build: ## Build Docker image
	docker build -t dacrew:latest .

docker-run: ## Run Docker container locally
	docker run -p 8000:8000 -v $(PWD)/config.yml:/app/config.yml:ro dacrew:latest

docker-compose-up: ## Start with Docker Compose
	docker-compose up --build

docker-compose-down: ## Stop Docker Compose
	docker-compose down

deploy: ## Deploy to local environment
	@echo "Deploying to local environment..."
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh

aws-deploy: ## Deploy to AWS (requires AWS credentials)
	@echo "Deploying to AWS..."
	@chmod +x scripts/deploy.sh
	@ENVIRONMENT=prod ./scripts/deploy.sh

update-embeddings: ## Update embeddings for all projects
	@echo "Updating embeddings..."
	@python -m dacrew.cli update-embeddings --help

list-projects: ## List configured projects
	@python -m dacrew.cli list-projects

status: ## Show project status
	@python -m dacrew.cli status

dev: ## Start development server
	uvicorn dacrew.server:app --reload --host 0.0.0.0 --port 8000

check: test lint ## Run all checks (tests + linting)

ci: check ## Run CI checks locally

all: clean install test lint build ## Run all steps
