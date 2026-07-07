default:
    @just --list

init:
    uv sync

test:
    uv run -m pytest

lint:
    uv run ruff check
    uv run ruff format --check
    uv run ty check src

fmt:
    uv run ruff format

hooks:
    uv run pre-commit run --all-files

docs:
    uv run mkdocs serve

build:
    uv build
