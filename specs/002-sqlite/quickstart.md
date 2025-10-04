# SQLitch Quickstart

This guide helps contributors get SQLitch running locally with full parity checks against Sqitch for SQLite, MySQL, and PostgreSQL.

## Prerequisites
- Python 3.11 (check with `python3 --version`)
- Git
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Sqitch Perl toolchain installed (for parity verification)

## 1. Clone & Branch
```bash
cd /path/to/work
git clone git@github.com:your-org/sqlitch-v3.git
cd sqlitch-v3
git checkout 001-we-re-going
```

## 2. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
```

## 3. Install Dependencies
```bash
pip install ".[dev]"
```
Includes runtime (Click, SQLAlchemy, psycopg[binary], PyMySQL, python-dateutil, pydantic) and tooling (pytest, pytest-cov, hypothesis, tox, black, isort, flake8, pylint, mypy, bandit, docker, rich). All subsequent commands assume the virtual environment remains activated.

## 4. Configure Docker Test Harness
```bash
# Ensure Docker daemon is running
scripts/docker-compose/up --detach
```
Provisioned services:
- `sqlitch-mysql`: MySQL 8.0 with seeded sqitch registry
- `sqlitch-postgres`: PostgreSQL 15 with seeded sqitch registry
- SQLite uses in-memory driver (no container)

## 5. Initialize Sample Project
- **Status**: Pending implementation (tasks T051–T056). Commands are not yet wired, so running this today raises `Error: No such command 'init'.`
- Once the CLI command surface lands, usage will look like:

	```bash
	cd examples/basic
	sqlitch init myapp --engine pg
	```

	- `sqlitch` installs as a console script (plus a compatibility shim in `bin/sqlitch` for direct invocation).
	- Detects existing `sqitch.*` files if copying samples; tool aborts if conflicting `sqlitch.*` detected.
	- Generated plan/scripts mirror Sqitch layout.

## 6. Run Test Suite
```bash
pytest --maxfail=1 --disable-warnings --cov=sqlitch --cov-report=term-missing
```
- Docker-backed tests auto-skip with warning when Docker unavailable; ensure coverage remains ≥90%.
- Mypy, pylint, flake8, isort, black, bandit enforced via `tox -e lint`.

## 7. Parity Smoke Test
```bash
# In comparisons/basic fixture
bin/sqlitch plan --json > sqlitch.json
sqitch plan --json > sqitch.json
diff -u sqitch.json sqlitch.json
```
Outputs must match byte-for-byte aside from change IDs where documented.

## 8. Tear Down
```bash
scripts/docker-compose/down
```
- Tests and examples must remove temporary directories and docker networks on completion.

## Troubleshooting
- **Docker not available**: Tests print `WARNING: Skipping dockerized engine tests (Docker unavailable)`.
- **PyMySQL import errors**: Ensure the virtual environment is activated; PyMySQL is pure Python, so reinstall with `pip install --force-reinstall pymysql` if the package appears missing.
- **psycopg binary dependency**: ensure `libpq` present (`brew install libpq`), add to `PATH` as needed.

## Next Steps
- Review `research.md` for design decisions and driver rationale.
- See `/contracts` for command-specific parity expectations.
- Follow `/plan.md` Phase 1 guidance before implementation.
