.PHONY: help setup run stop test demo clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - install dependencies
	@echo "🚀 Setting up FinOps AI Observability POC..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Setup complete! Run 'make run' to start the pipeline."

run: ## Run the pipeline locally
	@echo "🏃 Running FinOps AI pipeline..."
	./venv/bin/python src/main.py

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t finops-ai-poc:latest .

docker-run: ## Run with Docker Compose
	@echo "🐳 Starting stack with Docker Compose..."
	docker-compose up -d
	@echo "✅ Stack running! Dashboard: http://localhost:8080"

docker-stop: ## Stop Docker Compose stack
	@echo "⏹️  Stopping Docker Compose stack..."
	docker-compose down

test: ## Run end-to-end tests
	@echo "🧪 Running tests..."
	./venv/bin/python -m pytest tests/ -v

demo: ## Run demo with sample data
	@echo "🎬 Running demo..."
	./venv/bin/python src/main.py --demo

clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf venv
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete!"

logs: ## Show application logs
	docker-compose logs -f app

metrics: ## View Prometheus metrics
	@echo "📊 Opening metrics endpoints..."
	@echo "Application metrics: http://localhost:8000/metrics"
	@echo "Prometheus UI: http://localhost:9090"
	@echo "Dashboard: http://localhost:8080"

status: ## Check stack status
	@echo "📋 Docker Compose Status:"
	@docker-compose ps
	@echo ""
	@echo "📊 Endpoints:"
	@echo "  Dashboard:    http://localhost:8080"
	@echo "  Metrics:      http://localhost:8000/metrics"
	@echo "  Prometheus:   http://localhost:9090"

install-local: ## Install dependencies locally (without venv)
	pip install -r requirements.txt

run-local: ## Run locally without Docker
	@echo "🏃 Running locally..."
	cd src && python main.py

metrics: ## Open Prometheus metrics
	@echo "📊 Opening metrics at http://localhost:9090"
	open http://localhost:9090 || xdg-open http://localhost:9090

dashboard: ## Open dashboard
	@echo "📊 Opening dashboard at http://localhost:8080"
	open http://localhost:8080 || xdg-open http://localhost:8080
