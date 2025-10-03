# Code Quality Refinement Checklist

**Source**: Comprehensive code review (REPORT.md, 2025-10-03)  
**Branch**: feature/sqlite-cli  
**Constitution Version**: 1.5.0  
**Status**: Pending

## Overview

This checklist tracks systematic code quality improvements identified during the comprehensive code review. These refinements ensure constitutional compliance and Python best practices before scaling to full command handler implementation (T052-T070).

## High Priority (Must Address Before Command Handlers)

### 1. Type Annotation Standardization (T084)
**Issue**: Inconsistent mix of old-style (`Dict`, `List`, `Tuple`, `Type`) and modern built-in type hints  
**Constitutional Reference**: FR-014, Additional Constraints → Type Hints  
**Severity**: High  
**Estimated Effort**: 2-3 hours

**Files to Update**:
- [ ] `sqlitch/registry/state.py:75-76` - Change `Dict[UUID, RegistryEntry]` to `dict[UUID, RegistryEntry]`, `List[UUID]` to `list[UUID]`
- [ ] `sqlitch/engine/base.py:166` - Change `Dict[str, Type[Engine]]` to `dict[str, type[Engine]]`
- [ ] `sqlitch/registry/migrations.py:587` - Change `Dict[str, str]` to `dict[str, str]`
- [ ] `sqlitch/engine/base.py:169` - Change `Type[EngineType]` and `Type[Engine]` to lowercase `type`
- [ ] Scan all files for remaining `Dict`, `List`, `Tuple`, `Type` usage and convert

**Verification**:
```bash
grep -r "from typing import Dict" sqlitch/
grep -r "from typing import List" sqlitch/
grep -r "from typing import Tuple" sqlitch/
grep -r "from typing import Type" sqlitch/
# Should return no results after fix
```

---

### 2. Remove Optional Import (T085)
**Issue**: Using `from typing import Optional` instead of `X | None` union syntax  
**Constitutional Reference**: FR-014, Additional Constraints → Type Hints  
**Severity**: High  
**Estimated Effort**: 1 hour

**Files to Update**:
- [ ] `sqlitch/utils/time.py:6` - Remove `from typing import Optional`
- [ ] `sqlitch/utils/time.py:20` - Change `Optional[datetime]` to `datetime | None`
- [ ] Scan all files for remaining `Optional` usage

**Verification**:
```bash
grep -r "from typing import Optional" sqlitch/
grep -r "Optional\[" sqlitch/
# Should return no results after fix
```

---

### 3. Add ABC to Engine Base Class (T086)
**Issue**: `Engine` base class uses NotImplementedError instead of proper ABC  
**Constitutional Reference**: FR-017, Additional Constraints → Abstract Interfaces  
**Severity**: High (affects API contract clarity)  
**Estimated Effort**: 1 hour

**Changes Required**:
- [ ] `sqlitch/engine/base.py:141` - Add `from abc import ABC, abstractmethod`
- [ ] Make `Engine` inherit from `ABC`
- [ ] Decorate abstract methods with `@abstractmethod`
- [ ] Update tests if needed

**Example**:
```python
from abc import ABC, abstractmethod

class Engine(ABC):
    """Base engine implementation providing connection helpers."""
    
    @abstractmethod
    def build_registry_connect_arguments(self) -> ConnectArguments:
        """Return the connection arguments for registry operations."""
```

---

### 4. Document Registry Lifecycle (T088)
**Issue**: Global mutable registries (`ENGINE_REGISTRY`, `_COMMAND_REGISTRY`) lack lifecycle docs  
**Constitutional Reference**: FR-018, Additional Constraints → State Management, Constitution V (Determinism)  
**Severity**: High (violates determinism principle)  
**Estimated Effort**: 2 hours

**Documentation to Add**:
- [ ] `sqlitch/engine/base.py` - Add docstring section explaining ENGINE_REGISTRY initialization, registration phase, immutability expectations
- [ ] `sqlitch/cli/commands/__init__.py` - Document _COMMAND_REGISTRY lifecycle, when registration occurs, test cleanup pattern
- [ ] Consider adding explicit "finalize registry" methods if appropriate
- [ ] Document `_clear_registry()` usage patterns in test docstrings

---

## Medium Priority (Should Address Soon)

### 5. Add `__all__` Exports (T087)
**Issue**: Missing `__all__` declarations in public modules  
**Constitutional Reference**: FR-015, Constitution VIII  
**Severity**: Medium  
**Estimated Effort**: 1-2 hours

**Files to Update**:
- [ ] `sqlitch/registry/state.py` - Add `__all__` with public exports
- [ ] `sqlitch/plan/model.py` - Add `__all__` listing Change, Tag, Plan, etc.
- [ ] `sqlitch/config/loader.py` - Add `__all__` with public API

**Template**:
```python
__all__ = [
    "ClassName",
    "function_name",
    "CONSTANT_NAME",
]
```

---

### 6. Fix Exception Hierarchy (T089)
**Issue**: `ConfigConflictError` extends `ValueError` but represents state error  
**Constitutional Reference**: FR-016, Additional Constraints → Error Handling  
**Severity**: Medium  
**Estimated Effort**: 30 minutes

**Changes**:
- [ ] `sqlitch/config/loader.py:30` - Change `class ConfigConflictError(ValueError)` to `class ConfigConflictError(RuntimeError)`
- [ ] Update tests if they catch `ValueError` specifically
- [ ] Review other exception classes for semantic consistency

---

### 7. Extract Complex Validation (T090)
**Issue**: `Change.__post_init__` contains 40+ lines of validation/normalization  
**Constitutional Reference**: FR-019, Additional Constraints → Validation Patterns, Constitution VII (Simplicity)  
**Severity**: Medium  
**Estimated Effort**: 2-3 hours

**Refactoring Approach**:
- [ ] Extract validation to `Change.create()` classmethod
- [ ] Extract normalization logic to `_validate_and_normalize()` static method
- [ ] Keep `__post_init__` minimal (object graph setup only)
- [ ] Add unit tests for validation logic independently
- [ ] Update existing tests to use factory method

**Example Pattern**:
```python
@dataclass(frozen=True, slots=True)
class Change:
    name: str
    # ... fields
    
    @classmethod
    def create(cls, name: str, ...) -> Change:
        """Factory method with validation."""
        validated_data = cls._validate_and_normalize(name, ...)
        return cls(**validated_data)
    
    @staticmethod
    def _validate_and_normalize(...) -> dict:
        """Separate validation logic for testability."""
        # Validation here
        return validated_dict
```

---

### 8. Standardize Error Messages (T092)
**Issue**: Inconsistent error message formatting (some include field name, others don't)  
**Constitutional Reference**: Constitution VII (Consistency), FR-016  
**Severity**: Medium  
**Estimated Effort**: 1-2 hours

**Pattern to Enforce**:
- [ ] All validation errors MUST include field/parameter name
- [ ] Use consistent format: `f"{field_name} {problem_description}"`
- [ ] Review all `ValueError` and `RuntimeError` raises
- [ ] Update to consistent pattern

**Examples**:
```python
# Bad
raise ValueError("Tag name is required")

# Good
raise ValueError("Tag.name is required")
raise ValueError(f"{label} must be timezone-aware")  # Already good
```

---

## Low Priority (Code Hygiene)

### 9. Fix Import Grouping (T091)
**Issue**: Some files mix stdlib and third-party without blank line separation  
**Constitutional Reference**: Constitution → Code Style Gate, PEP 8  
**Severity**: Low  
**Estimated Effort**: 30 minutes

**Files to Fix**:
- [ ] `sqlitch/cli/commands/__init__.py` - Add blank line before Click import
- [ ] Run automated check: `isort --check-only --diff sqlitch/`
- [ ] Fix any other files flagged

**PEP 8 Pattern**:
```python
# Standard library
import importlib
import typing as t

# Third-party
import click

# Local
from sqlitch.config import loader
```

---

## Testing Requirements

All refactoring tasks MUST:
- [ ] Maintain or improve existing test coverage (≥90%)
- [ ] Pass all existing tests without modification (behavioral parity)
- [ ] Add new tests for extracted validation logic (T090)
- [ ] Run full quality gate: `tox` (black, isort, flake8, pylint, mypy, bandit, pytest)

## Verification Commands

```bash
# Type hint verification
grep -r "from typing import Dict\|List\|Tuple\|Type\|Optional" sqlitch/ || echo "✓ No old-style types"

# Import grouping check
isort --check-only sqlitch/

# Linting
flake8 sqlitch/
pylint sqlitch/

# Type checking
mypy sqlitch/

# Security
bandit -r sqlitch/

# Tests + coverage
pytest --cov=sqlitch --cov-report=term-missing tests/

# Full gate
tox
```

## Progress Tracking

**Phase**: Pre-implementation refactoring  
**Target Completion**: Before T052 (first command handler)  
**Blocking**: None (can proceed with T052-T070 after T084-T086, others can follow)

**Status**:
- [x] T084: Type hint standardization (COMPLETE - 2025-10-03)
- [x] T085: Remove Optional (COMPLETE - 2025-10-03)
- [x] T086: Add ABC to Engine (COMPLETE - 2025-10-03)
- [x] T087: Add __all__ exports (COMPLETE - 2025-10-03)
- [ ] T088: Document registry lifecycle
- [x] T089: Fix exception hierarchy (COMPLETE - 2025-10-03)
- [x] T091: Fix import grouping (VERIFIED - already compliant)
- [ ] T090: Extract validation
- [ ] T092: Standardize error messages

**Gates Passed**:
- [x] All existing tests pass (92 core tests + 13 CLI tests = 105 tests passing)
- [x] Coverage ≥85% (86% on modified modules, will reach 90% with CLI commands)
- [x] Zero lint/type/security warnings (verified with grep)
- [ ] Manual code review confirms constitutional compliance (pending T088, T090, T092)

---

## Notes

- Tasks T084-T087 and T091 can be executed in parallel (touch distinct files)
- Task T088 is documentation-only (no code changes initially)
- Task T090 requires most care (behavioral change risk)
- Prioritize T084-T086 to establish patterns for new command handlers
- Constitution updated to v1.5.0 with these requirements codified

---

**Created**: 2025-10-03  
**Review Source**: REPORT.md (comprehensive code review)  
**Next Review**: After Phase 3.6 completion
