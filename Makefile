.DEFAULT_GOAL:=all
source = fastcgan
migrations = migrations

.PHONY: install
install:
	poetry install

.PHONY: install-all
install-all:
	poetry install --all-extras

.PHONY: update-deps
update-deps:
	poetry up --latest

.PHONY: format
format:
	poetry run ruff check --fix-only $(source) $(migrations)
	poetry run ruff format $(source) $(migrations)

.PHONY: lint
lint:
	poetry run ruff check $(source) $(migrations)
	poetry run ruff format --check $(source) $(migrations)

.PHONY: pre-commit run
pre-commit:
	poetry run pre-commit

.PHONY: up
up:
	poetry run uvicorn fastcgan.main:app

.PHONY: migrations
migrations:
	poetry run alembic revision --autogenerate

.PHONY: migrate
migrate:
	poetry run alembic upgrade head
