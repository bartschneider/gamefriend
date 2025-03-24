# CLAUDE.md - Guide for Agentic Coding Assistants

## Commands
- **Backend**: `poetry run uvicorn gamefriend.main:app --reload`
- **Frontend**: `cd frontend && pnpm dev`
- **Test**: `poetry run pytest tests/` (Single test: `pytest tests/test_file.py::test_function`)
- **Lint**: `poetry run flake8` or `make lint`
- **Format**: `poetry run black . && poetry run isort .` or `make format`
- **Type Check**: `poetry run mypy gamefriend tests` or `make type-check`
- **Frontend Lint**: `cd frontend && pnpm lint`
- **Full Check**: `make check-all`

## Code Style
- **Python**: Follow PEP 8, use type annotations throughout
- **Import Order**: stdlib → third-party → internal (use isort)
- **Python Formatting**: Black with default settings
- **Error Handling**: Use explicit exception handling with custom exceptions
- **Naming**: snake_case for Python, camelCase for JavaScript/TypeScript
- **Types**: Use explicit typing in Python, TypeScript for frontend
- **React Patterns**: Function components with hooks, shadcn/ui design system

This project is a Next.js + FastAPI application for AI-powered gaming guide assistance.