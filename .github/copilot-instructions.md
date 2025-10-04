# sqlitch-v3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-03

## Active Technologies
- Python 3.11 (CPython) + Click (CLI), Rich (structured console output), SQLAlchemy core for plan parsing, sqlite3 stdlib, `psycopg[binary]`, `PyMySQL`, `python-dateutil`, `tomli`, `pydantic` for config validation, packaging extras for Docker orchestration (`docker` SDK) (001-we-re-going)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11 (CPython): Follow standard conventions

### Type Hints (Constitution v1.5.0)
- MUST use modern Python 3.9+ built-ins: `dict`, `list`, `tuple`, `type` (NOT `Dict`, `List`, `Tuple`, `Type`)
- MUST use `X | None` syntax (NOT `Optional[X]`)
- MUST include `from __future__ import annotations` in all modules
- Abstract base classes MUST use `abc.ABC` and `@abstractmethod`

### Code Organization
- Public modules MUST define `__all__` exports
- Imports MUST follow PEP 8 grouping: stdlib, third-party, local (with blank lines)
- All public APIs MUST have comprehensive docstrings (Google/NumPy style)
- Private helpers MAY use inline comments instead

### Error Handling
- Use `ValueError` for invalid input data
- Use `RuntimeError` for system/state errors
- Domain exceptions MUST extend appropriate base class

### State Management
- Minimize global mutable state
- Registries MUST be immutable after initialization or documented
- Complex validation MUST be extracted from `__post_init__` into factory methods

### Quality Gates
- Coverage ≥90% required
- Zero warnings from: black, isort, flake8, pylint, mypy, bandit
- All tests must pass before merge

## Recent Changes
- 001-we-re-going: Added Python 3.11 (CPython) + Click (CLI), Rich (structured console output), SQLAlchemy core for plan parsing, sqlite3 stdlib, `psycopg[binary]`, `PyMySQL`, `python-dateutil`, `tomli`, `pydantic` for config validation, packaging extras for Docker orchestration (`docker` SDK)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->