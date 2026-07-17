.PHONY: install fmt lint typecheck test check

install:
	uv sync --dev

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run ty check

test:
	uv run pytest

check:
	uv run ruff check .
	uv run ty check
	uv run pytest
