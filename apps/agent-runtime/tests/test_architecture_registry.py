"""Tests for the architecture registry — register() decorator and get_executor() lookup."""

import pytest

from app.architectures import REGISTRY, get_executor

# Ensure architecture modules are imported (triggers @register side-effects)
import app.architectures.centralized  # noqa: F401
import app.architectures.workflow  # noqa: F401
import app.architectures.swarm  # noqa: F401

from app.architectures.centralized import CentralizedExecutor
from app.architectures.workflow import WorkflowExecutor
from app.architectures.swarm import SwarmExecutor


def test_registry_has_exactly_three_entries() -> None:
    assert len(REGISTRY) == 3


@pytest.mark.parametrize(
    "key,expected_cls",
    [
        ("centralized_orchestration", CentralizedExecutor),
        ("structured_workflow", WorkflowExecutor),
        ("decentralized_swarm", SwarmExecutor),
    ],
)
def test_get_executor_returns_correct_instance(key: str, expected_cls: type) -> None:
    executor = get_executor(key)
    assert isinstance(executor, expected_cls)


def test_get_executor_raises_key_error_for_unknown_mode() -> None:
    with pytest.raises(KeyError, match="Unknown architecture"):
        get_executor("unknown_mode")
