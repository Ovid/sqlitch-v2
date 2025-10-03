"""Base engine abstractions for SQLitch."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from types import MappingProxyType, ModuleType
from typing import Any, Dict, Mapping, Tuple, Type, TypeVar


class EngineError(RuntimeError):
    """Base exception class for engine-related failures."""


class UnsupportedEngineError(EngineError):
    """Raised when an engine is not known or has not been registered."""


@dataclass(frozen=True, slots=True)
class ConnectArguments:
    """Container for positional and keyword arguments passed to a driver."""

    args: Tuple[Any, ...] = field(default_factory=tuple)
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
    """Callable factory that loads a Python DB-API driver on demand."""

    __slots__ = ("engine", "module_name", "connect_attribute")

    def __init__(self, engine: str, module_name: str, connect_attribute: str = "connect") -> None:
        self.engine = engine
        self.module_name = module_name
        self.connect_attribute = connect_attribute

    def connect(self, arguments: ConnectArguments) -> Any:
        module = _import_module(self.module_name)
        connect_callable = getattr(module, self.connect_attribute)
        return connect_callable(*arguments.args, **arguments.kwargs)


ENGINE_DRIVERS: Mapping[str, Tuple[str, str]] = MappingProxyType(
    {
        "sqlite": ("sqlite3", "connect"),
        "pg": ("psycopg", "connect"),
        "mysql": ("pymysql", "connect"),
    }
)


def connection_factory_for_engine(engine: str) -> ConnectionFactory:
    canonical = canonicalize_engine_name(engine)

    driver = ENGINE_DRIVERS.get(canonical)
    if driver is None:
        raise UnsupportedEngineError(f"no driver registered for engine {canonical!r}")

    module_name, connect_attribute = driver
    return ConnectionFactory(canonical, module_name, connect_attribute)


EngineType = TypeVar("EngineType", bound="Engine")


class Engine:
    """Base engine implementation."""

    def __init__(self, target: EngineTarget, **_: Any) -> None:
        self.target = target
        self._connection_factory = connection_factory_for_engine(target.engine)

    def build_registry_connect_arguments(self) -> ConnectArguments:
        raise NotImplementedError

    def build_workspace_connect_arguments(self) -> ConnectArguments:
        raise NotImplementedError

    def connect_registry(self) -> Any:
        arguments = self.build_registry_connect_arguments()
        return self._connection_factory.connect(arguments)

    def connect_workspace(self) -> Any:
        arguments = self.build_workspace_connect_arguments()
        return self._connection_factory.connect(arguments)


ENGINE_REGISTRY: Dict[str, Type[Engine]] = {}


def register_engine(name: str, engine_cls: Type[EngineType], *, replace: bool = False) -> Type[Engine] | None:
    canonical = canonicalize_engine_name(name)
    if not issubclass(engine_cls, Engine):
        raise TypeError("engine_cls must be a subclass of Engine")

    previous = ENGINE_REGISTRY.get(canonical)
    if previous is not None and not replace:
        raise EngineError(f"engine {canonical!r} already registered")

    ENGINE_REGISTRY[canonical] = engine_cls
    return previous


def unregister_engine(name: str) -> Type[Engine] | None:
    canonical = canonicalize_engine_name(name)
    return ENGINE_REGISTRY.pop(canonical, None)


def create_engine(target: EngineTarget, **kwargs: Any) -> Engine:
    engine_cls = ENGINE_REGISTRY.get(target.engine)
    if engine_cls is None:
        raise UnsupportedEngineError(f"engine {target.engine!r} is not registered")
    return engine_cls(target, **kwargs)


def registered_engines() -> Tuple[str, ...]:
    return tuple(sorted(ENGINE_REGISTRY.keys()))


def _import_module(module_name: str) -> ModuleType:
    return importlib.import_module(module_name)

