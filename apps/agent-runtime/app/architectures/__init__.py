"""Architecture registry — register() decorator and get_executor() lookup.

Each architecture module uses @register("key") to self-register when imported.
"""

from __future__ import annotations

from app.architectures.base import ArchitectureExecutor, ExecutionContext, ExecutionResult

__all__ = [
    "ArchitectureExecutor",
    "ExecutionContext",
    "ExecutionResult",
    "REGISTRY",
    "get_executor",
    "register",
]

REGISTRY: dict[str, type[ArchitectureExecutor]] = {}


def register(key: str):
    """Class decorator that registers an architecture executor under *key*."""
    def decorator(cls: type[ArchitectureExecutor]) -> type[ArchitectureExecutor]:
        REGISTRY[key] = cls
        return cls
    return decorator


def get_executor(architecture_mode: str) -> ArchitectureExecutor:
    """Return an instance of the executor registered for *architecture_mode*."""
    cls = REGISTRY.get(architecture_mode)
    if cls is None:
        raise KeyError(f"Unknown architecture: {architecture_mode}")
    return cls()
