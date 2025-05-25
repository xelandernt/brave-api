default: install lint test

install:
    uv lock --upgrade
    uv sync --all-extras --frozen
    @just hook

lint:
    uv run pre-commit run ruff --all-files
    uv run pre-commit run ruff-format --all-files
    uv run pre-commit run mypy --all-files
    uv run pre-commit run end-of-file-fixer --all-files
    uv run pre-commit run mixed-line-ending --all-files
    uv run pre-commit run codespell --all-files


test *args:
    uv run --no-sync pytest {{ args }}

publish:
    rm -rf dist
    uv build
    uv publish --token $PYPI_TOKEN

hook:
    uv run pre-commit install --install-hooks --overwrite

unhook:
    uv run pre-commit uninstall

docs:
    uv pip install -r docs/requirements.txt
    uv run mkdocs serve
