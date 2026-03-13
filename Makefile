PYTHON = uv run
FRONTEND_NPM = npm --prefix frontend

.PHONY: dev-backend dev-frontend test seed reset-db

dev-backend:
	$(PYTHON) uvicorn backend.app.main:app --reload

dev-frontend:
	$(FRONTEND_NPM) run dev

test:
	$(PYTHON) pytest

seed:
	$(PYTHON) python -m backend.app.seed.cli

reset-db:
	rm -f backend/rugby_director.db
	$(PYTHON) python -m backend.app.seed.cli
