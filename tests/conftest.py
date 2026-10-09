"""Shared test helpers.

FakePlanner stands in for the supervisor's LLM. A test scripts the plan it
wants, so no real model is called.
"""

import pytest

from retail_support.model_provider import ModelProvider
from retail_support.supervisor import RoutingPlan, WorkerTask


class FakePlanner:
    """Returns one scripted plan per call and records what it was asked."""

    def __init__(self, plans, error=None):
        self.plans = list(plans)
        self.error = error
        self.seen = []  # the messages of each call, in order
        self.configs = []  # the config of each call, in order

    def with_structured_output(self, schema):
        return self

    async def ainvoke(self, messages, config=None):
        self.seen.append(messages)
        self.configs.append(config)
        if self.error is not None:
            raise self.error
        tasks = self.plans[len(self.seen) - 1]
        return RoutingPlan(
            tasks=[WorkerTask(worker=worker, question=q) for worker, q in tasks]
        )


@pytest.fixture
def use_planner(monkeypatch):
    """Replace the supervisor's LLM with a FakePlanner.

    use_planner(plan_1, plan_2, ...) returns the FakePlanner.
    Each plan is a list of (worker, question) pairs, one plan per LLM call.
    use_planner(error=SomeError("...")) makes every call fail.
    """

    def _use(*plans, error=None):
        planner = FakePlanner(plans, error=error)
        monkeypatch.setattr(ModelProvider, "get", lambda role: planner)
        return planner

    return _use
