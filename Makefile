POETRY = poetry run
UVICORN = poetry run uvicorn

GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[1;33m
NC = \033[0m

HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: help runserver lint seed_data

help:
	@echo "$(YELLOW)Available targets:$(NC)"
	@echo "  $(GREEN)runserver$(NC)      - Start FastAPI development server"
	@echo "  $(GREEN)lint$(NC)           - Run flake8, isort, mypy linters"
	@echo "  $(GREEN)seed_data$(NC)           - Seed the database"

runserver:
	@echo "$(GREEN)Starting FastAPI server...$(NC)"
	$(UVICORN) src.main:app --reload --host $(HOST) --port $(PORT)

lint:
	@echo "$(GREEN)Running linters...$(NC)"
	$(POETRY) black .
	$(POETRY) isort .
	$(POETRY) flake8 .
	$(POETRY) mypy .

seed:
	@echo "$(GREEN)Seeding database...$(NC)"
	$(POETRY) python scripts/seed_db.py
