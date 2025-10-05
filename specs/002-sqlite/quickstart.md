# SQLitch Quickstart (SQLite MVP)

This guide helps contributors validate the SQLite-focused MVP while confirming that the multi-engine framework and scaffolding are ready for future adapters.

## Prerequisites
- Python 3.11 (check with `python3 --version`)
- Git
- Docker Desktop (macOS/Windows) or Docker Engine (Linux) *(optional for M1; used to verify skip behavior and maintain container scaffolding)*
- Sqitch Perl toolchain installed (for parity verification)

## 1. Clone & Branch
```bash
cd /path/to/work
git clone git@github.com:your-org/sqlitch-v3.git
cd sqlitch-v3
git checkout 002-sqlite
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

## 4. (Optional) Start Docker Test Harness
```bash
# Ensure Docker daemon is running
scripts/docker-compose/up --detach
```
Provisioned services (used for future milestones and to confirm skipped suites stay gated):
- `sqlitch-mysql`: MySQL 8.0 with seeded Sqitch registry
- `sqlitch-postgres`: PostgreSQL 15 with seeded Sqitch registry
- SQLite uses local files/in-memory driver (no container)

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
	- Credentials resolve flags → environment (`SQLITCH_PASSWORD`, `SQLITCH_PG_URI`, etc.) → config files, and secrets are never written back to disk or echoed in logs.

## 6. Run Test Suite (Full Matrix)
```bash
pytest --maxfail=1 --disable-warnings --cov=sqlitch --cov-report=term-missing
```
- Ensure the full suite runs so that placeholder MySQL/PostgreSQL suites are exercised and remain skipped with warnings when Docker or adapters are unavailable.
- Coverage MUST remain ≥90% and lint/type/security checks are enforced via `tox -e lint`.
- Mypy, pylint, flake8, isort, black, bandit enforced via `tox -e lint`.

## 7. Parity Smoke Test
```bash
# In comparisons/basic fixture
bin/sqlitch plan --json > sqlitch.json
sqitch plan --json > sqitch.json
diff -u sqitch.json sqlitch.json
```
Outputs must match byte-for-byte aside from documented change ID differences for SQLite. Stubs for other engines raise `NotImplementedError` until their milestones begin.

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
- Follow `/plan.md` Phase 1 guidance before implementation and keep MySQL/PostgreSQL work stubbed until their dedicated milestones kick off.
