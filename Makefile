.PHONY: install run run-dev test check lint format clean docker-up docker-down

install:
	pip install -e .

run:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

run-dev:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -v

check:
	python3 scripts/dead_code_check.py

lint:
	ruff check .

format:
	ruff format .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache .ruff_cache

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
