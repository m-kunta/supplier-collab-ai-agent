.PHONY: setup dev api ui test lint

# Setup both Python backend and Node.js frontend environments
setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

# Start both servers concurrently
dev:
	@chmod +x scripts/dev.sh
	@./scripts/dev.sh

# Start only the backend API
api:
	.venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Start only the frontend UI
ui:
	cd frontend && npm run dev

# Run all tests (Python and Node)
test:
	.venv/bin/pytest
	cd frontend && npm run test -- --run

# Lint Python code
lint:
	.venv/bin/ruff check .
