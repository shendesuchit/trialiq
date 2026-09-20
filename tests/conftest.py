"""Pytest configuration for deterministic local and CI test runs."""

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip live-service tests unless the caller explicitly opts in."""

    if os.getenv("TRIALIQ_RUN_INTEGRATION") == "1":
        return

    skip_integration = pytest.mark.skip(
        reason=(
            "integration test requires Neo4j; set "
            "TRIALIQ_RUN_INTEGRATION=1 to run it"
        )
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
