# Security Findings and Suppressions

**Last Updated**: 2025-10-11  
**Lockdown Phase**: 005

## Summary

This document tracks security findings from pip-audit and bandit scans, documents suppressed warnings with rationale, and notes remediation plans for unresolved issues.

## pip-audit Findings

### Known Vulnerabilities

#### CVE-2025-8869: pip 25.2 Tarfile Extraction Vulnerability

**Status**: ⚠️ UNRESOLVED (awaiting upstream fix)  
**Severity**: HIGH  
**Advisory**: GHSA-4xh5-x5gv-qwph

**Description:**  
In the fallback extraction path for source distributions, pip used Python's tarfile module without verifying that symbolic/hard link targets resolve inside the intended extraction directory. A malicious sdist can include links that escape the target directory and overwrite arbitrary files during `pip install`.

**Impact:**  
Successful exploitation enables arbitrary file overwrite outside the build/extraction directory. This can be leveraged to tamper with configuration or startup files.

**Conditions:**  
Triggered when installing an attacker-controlled sdist (e.g., from an index or URL) and the fallback extraction code path is used.

**Remediation Plan:**  
- Upstream fix planned for pip 25.3 (not yet released as of 2025-10-11)
- Monitor https://github.com/pypa/pip/pull/13550 for release status
- Consider using Python interpreter with PEP 706 safe-extraction behavior for defense in depth
- Document warning in CONTRIBUTING.md advising users to avoid installing untrusted packages

**Workaround:**  
Use Python 3.11+ which implements safer tarfile handling (partial mitigation).

**SQLitch Exposure:**  
SQLitch does not programmatically install packages from untrusted sources. Risk limited to developer environments during `pip install`.

---

## bandit Findings

### Suppressed Warnings (False Positives)

#### B303, B324: Use of Weak SHA1 Hash

**Files:**
- `sqlitch/utils/identity.py` (line 128)
- `sqlitch/cli/commands/deploy.py` (lines 1022, 1462)

**Rationale:**  
SHA1 is used for Sqitch-compatible change ID generation and script checksumming, NOT for cryptographic security purposes. These are content hashes matching upstream Sqitch behavior and registry schema.

**Why Safe:**  
- Change IDs are Git-style object hashes for content addressing, not password hashing
- Script checksums verify integrity, not authenticity
- No security properties depend on collision resistance
- Must match Sqitch's SHA1 usage for registry compatibility

**Suppression:** Added to `.bandit` configuration.

---

#### B608: Hardcoded SQL Expressions (f-strings with schema names)

**Files:**
- `sqlitch/cli/commands/deploy.py` (multiple locations)
- `sqlitch/cli/commands/revert.py` (multiple locations)

**Rationale:**  
SQL f-strings use `registry_schema` variable which comes from validated engine configuration, not user input. All actual user data is properly parameterized using `?` placeholders.

**Why Safe:**  
- `registry_schema` is an internal identifier validated by engine layer
- Schema/table names cannot be parameterized in SQL (language limitation)
- All user-controlled values (project, change_id, etc.) use proper parameterization
- No SQL injection vector exists

**Example Safe Pattern:**
```python
# Safe: schema from config, data parameterized
cursor.execute(
    f"SELECT change_id FROM {registry_schema}.changes WHERE project = ?",
    (project,)  # user input properly parameterized
)
```

**Suppression:** Added to `.bandit` configuration.

---

### Remaining Low-Severity Issues

#### B110: Try, Except, Pass Detected

**Files:**
- `sqlitch/utils/identity.py` (line 364) - Windows-specific fallback
- Various other locations

**Status**: ACCEPTED  
**Rationale:**  
These are legitimate fallback handlers for optional identity detection (e.g., Windows API calls that may not exist). They are covered by `# pragma: no cover` comments and have safer defaults in the calling code.

**No Action Required**: Low severity, intentional design.

---

## Security Best Practices

### SQL Injection Prevention

✅ **All user inputs are parameterized**  
- Change names, project names, timestamps, emails: all use `?` placeholders
- Schema/table names come from internal configuration only

✅ **Path validation**  
- Template paths validated against allowed directories
- Deploy/revert/verify scripts resolved within project boundaries

✅ **Configuration validation**  
- URI parsing and validation before database connections
- Credential resolution follows strict precedence chain

### Dependency Management

✅ **Regular pip-audit runs**  
- Scheduled as part of release checklist (T050)
- Unresolved CVEs documented with remediation plans

✅ **Minimal dependency surface**  
- Core dependencies: Click, sqlite3 (stdlib), pytest
- Optional dependencies (MySQL/PostgreSQL) isolated

### Code Quality

✅ **Type safety**  
- mypy --strict enforced on core modules
- Explicit type hints reduce runtime surprises

✅ **Test isolation**  
- All tests use isolated filesystem contexts
- No pollution of user configuration directories

---

## Release Checklist

Before each release:

1. Run security scans:
   ```bash
   pip-audit --format json > artifacts/pip-audit.json
   bandit -r sqlitch/ -c .bandit -f json -o artifacts/bandit.json
   ```

2. Review new findings:
   - HIGH severity: block release, must fix or document
   - MEDIUM severity: evaluate case-by-case
   - LOW severity: acceptable with documented rationale

3. Update this document:
   - Add new suppressions with rationale
   - Update remediation plans for unresolved issues
   - Note any dependency upgrades

4. Verify `.bandit` configuration:
   - All suppressions have documented rationale
   - No blanket disables of entire test categories
   - Regular review of suppressed tests

---

## References

- pip-audit: https://pypi.org/project/pip-audit/
- bandit: https://bandit.readthedocs.io/
- OWASP SQL Injection: https://owasp.org/www-community/attacks/SQL_Injection
- CVE-2025-8869: https://github.com/advisories/GHSA-4xh5-x5gv-qwph
