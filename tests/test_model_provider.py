import pytest

from retail_support.model_provider import (
    PROVIDER_BUILDERS,
    ROLE_SPECS,
    ModelProvider,
    ModelSpec,
)


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        ModelProvider.get(role="hacker")


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setitem(ROLE_SPECS, "support", ModelSpec("nope", "m", 0.0, None))

    with pytest.raises(ValueError):
        ModelProvider.get(role="support")


def test_role_is_built_by_its_provider(monkeypatch):
    monkeypatch.setitem(PROVIDER_BUILDERS, "groq", lambda spec: ("built", spec))

    assert ModelProvider.get(role="supervisor") == ("built", ROLE_SPECS["supervisor"])
