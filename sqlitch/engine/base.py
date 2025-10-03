"""Base engine abstractions for SQLitch."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
import importlib
from types import MappingProxyType, ModuleType
from typing import Any, TypeVar


class EngineError(RuntimeError):
    """Base exception class for engine-related failures."""


class UnsupportedEngineError(EngineError):
    """Raised when an engine is not known or has not been registered."""


@dataclass(frozen=True, slots=True)
class ConnectArguments:
    """Container for positional and keyword arguments passed to a driver."""

    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))
        object.__setattr__(
            self,
            "kwargs",
            MappingProxyType(dict(self.kwargs)),
        )


ENGINE_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "pg": "pg",
        "postgres": "pg",
        "postgresql": "pg",
        "sqlite": "sqlite",
        "sqlite3": "sqlite",
        "mysql": "mysql",
        "mariadb": "mysql",
    }
)


def canonicalize_engine_name(name: str) -> str:
    """Return the canonical name for an engine.

    Raises:
        UnsupportedEngineError: If no canonical name is known.
    """

    key = name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    canonical = ENGINE_ALIASES.get(key)
    if canonical is None:
        raise UnsupportedEngineError(f"unsupported engine: {name!r}")
    return canonical


@dataclass(slots=True)
class EngineTarget:
    """Description of a registry/workspace engine target."""

    name: str
    engine: str
    uri: str
    variables: Mapping[str, str] = field(default_factory=dict)

    registry_uri: str = field(init=False)

    def __post_init__(self) -> None:
        canonical = canonicalize_engine_name(self.engine)
        object.__setattr__(self, "engine", canonical)
        object.__setattr__(self, "registry_uri", self.uri)

        variables = {str(key): str(value) for key, value in dict(self.variables).items()}
        object.__setattr__(self, "variables", MappingProxyType(variables))


class ConnectionFactory:
    """Callable factory that loads a Python DB-API driver on demand.

    Instances know the canonical engine name, the module path to import, and the
    attribute that exposes the DB-API ``connect`` callable. They provide a
    uniform ``connect`` method so higher layers can remain agnostic to driver
    specifics.
    """

    __slots__ = ("engine", "module_name", "connect_attribute")

    def __init__(self, engine: str, module_name: str, connect_attribute: str = "connect") -> None:
        self.engine = engine
        self.module_name = module_name
        self.connect_attribute = connect_attribute

    def connect(self, arguments: ConnectArguments) -> Any:
        """Import the configured driver and invoke its ``connect`` function."""
        module = _import_module(self.module_name)
        connect_callable = getattr(module, self.connect_attribute)
        return connect_callable(*arguments.args, **arguments.kwargs)


ENGINE_DRIVERS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "sqlite": ("sqlite3", "connect"),
        "pg": ("psycopg", "connect"),
        "mysql": ("pymysql", "connect"),
    }
)


def connection_factory_for_engine(engine: str) -> ConnectionFactory:
    """Return a :class:`ConnectionFactory` for the requested engine.

    Args:
        engine: Engine identifier or alias (case-insensitive).

    Raises:
        UnsupportedEngineError: If no driver mapping exists for ``engine``.
    """
    canonical = canonicalize_engine_name(engine)

    driver = ENGINE_DRIVERS.get(canonical)
    if driver is None:
        raise UnsupportedEngineError(f"no driver registered for engine {canonical!r}")

    module_name, connect_attribute = driver
    return ConnectionFactory(canonical, module_name, connect_attribute)


EngineType = TypeVar("EngineType", bound="Engine")


class Engine(ABC):
    """Base engine implementation providing connection helpers.

    Subclasses specialise the construction of connection arguments for their
    registry and workspace databases while sharing lazy driver loading logic.
    """

    def __init__(self, target: EngineTarget, **_: Any) -> None:
        self.target = target
        self._connection_factory = connection_factory_for_engine(target.engine)

    @abstractmethod
    def build_registry_connect_arguments(self) -> ConnectArguments:
        """Return the connection arguments for registry operations."""

    @abstractmethod
    def build_workspace_connect_arguments(self) -> ConnectArguments:
        """Return the connection arguments for workspace operations."""

    def connect_registry(self) -> Any:
        """Open a connection to the engine's registry database."""
        arguments = self.build_registry_connect_arguments()
        return self._connection_factory.connect(arguments)

    def connect_workspace(self) -> Any:
        """Open a connection to the engine's workspace database."""
        arguments = self.build_workspace_connect_arguments()
        return self._connection_factory.connect(arguments)


ENGINE_REGISTRY: dict[str, type[Engine]] = {}
"""Global registry mapping engine names to their implementation classes.

**Lifecycle & Thread Safety:**

1. **Registration Phase** (module import time):
   - Engine implementations register themselves via :func:`register_engine`
   - Occurs during module import (e.g., ``sqlitch.engine.sqlite`` imports trigger registration)
   - Registration is deterministic and occurs before application logic runs

2. **Operational Phase** (after imports complete):
   - Registry is effectively immutable once all modules are loaded
   - Lookups via :func:`get_engine` are thread-safe (dict reads are atomic in CPython)
   - No modifications should occur after initial registration

3. **Test Isolation:**
   - Tests should NOT modify this global registry
   - Each test should use isolated engine instances
   - If tests absolutely must modify the registry, they should restore the original state

**Example Usage:**

    >>> from sqlitch.engine import get_engine
    >>> engine_cls = get_engine("sqlite")
    >>> engine = engine_cls(config)

**Warning:**
    Modifying this registry after module initialization may lead to race conditions
    or inconsistent behavior across concurrent operations. The registry is considered
    frozen once :func:`get_engine` is first called.
"""


def register_engine(name: str, engine_cls: type[EngineType], *, replace: bool = False) -> type[Engine] | None:
    """Register an :class:`Engine` implementation under ``name``.

    Args:
        name: Engine identifier or alias.
        engine_cls: Concrete subclass implementing :class:`Engine`.
        replace: Whether to replace an existing registration.

    Returns:
        The previously registered engine class if ``replace`` is ``True`` and an
        entry existed; otherwise :data:`None`.

    Raises:
        UnsupportedEngineError: If ``name`` cannot be canonicalized.
        TypeError: If ``engine_cls`` is not a subclass of :class:`Engine`.
        EngineError: If the engine is already registered and ``replace`` is
            :data:`False`.
    """
    canonical = canonicalize_engine_name(name)
    if not issubclass(engine_cls, Engine):
        raise TypeError("engine_cls must be a subclass of Engine")

    previous = ENGINE_REGISTRY.get(canonical)
    if previous is not None and not replace:
        raise EngineError(f"engine {canonical!r} already registered")

    ENGINE_REGISTRY[canonical] = engine_cls
    return previous


def unregister_engine(name: str) -> type[Engine] | None:
    """Remove the engine associated with ``name`` and return it if present."""
    canonical = canonicalize_engine_name(name)
    return ENGINE_REGISTRY.pop(canonical, None)


def create_engine(target: EngineTarget, **kwargs: Any) -> Engine:
    """Instantiate the registered engine for ``target``.

    Keyword arguments are forwarded to the engine constructor.

    Raises:
        UnsupportedEngineError: If no engine has been registered for the target.
    """
    engine_cls = ENGINE_REGISTRY.get(target.engine)
    if engine_cls is None:
        raise UnsupportedEngineError(f"engine {target.engine!r} is not registered")
    return engine_cls(target, **kwargs)


def registered_engines() -> tuple[str, ...]:
    """Return the sorted tuple of canonical engine names currently registered."""
    return tuple(sorted(ENGINE_REGISTRY.keys()))


def _import_module(module_name: str) -> ModuleType:
    return importlib.import_module(module_name)

