# Quickstart: Quality Lockdown Validation

## Prerequisites
- **Sqitch v1.5.3** installed and available in PATH (for UAT testing)
  - The vendored `sqitch/` directory contains v1.5.3 for reference
  - Install via: `brew install sqitch` (macOS) or equivalent

## 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 2. Baseline Quality Gates
```bash
pytest --cov=sqlitch --cov-report=term --cov-report=html
mypy --strict sqlitch/
pydocstyle sqlitch/
pip-audit
bandit -r sqlitch/
```
- Inspect `htmlcov/index.html` for modules below 90% coverage (focus on resolver, registry state, identity helpers).
- Log outputs for auditing include `coverage.xml` and `bandit.json` (if generated).

## 3. Manual UAT Compatibility Scripts (SQLite Tutorial)
```bash
# Prepare clean working dirs (scripts perform cleanup automatically)
python uat/side-by-side.py --out artifacts/side-by-side.log
python uat/forward-compat.py --out artifacts/forward-compat.log
python uat/backward-compat.py --out artifacts/backward-compat.log
```
- Ensure each script exits with code 0.
- Review sanitized logs for behavioral differences; cosmetic diffs (case, whitespace) acceptable.
- Capture final confirmation comment for release PR (see Step 5).

## 4. Documentation & Checklist Updates
- Update README quickstart section, troubleshooting guide, and CONTRIBUTING instructions with any new steps discovered.
- Record coverage exceptions (if any) with rationale.

## 5. Release Pull Request Comment Template
```
UAT Compatibility Run (SQLite tutorial)
- Side-by-side: ✅ (log: <link>)
- Forward compat: ✅ (log: <link>)
- Backward compat: ✅ (log: <link>)
Notes: <surface any observed cosmetic diffs>
```

## 6. Final Verification
```bash
pytest
python -m tox  # optional full gate when ready
```
- Confirm all constitutional gates satisfied prior to tagging v1.0.0.
