# Change Start: Add deterministic LLM factory tests

from unittest.mock import patch

import pytest

from trialiq.llm.factory import _require_value, create_llm


def test_require_value_returns_non_empty_value():
    assert _require_value("configured-value", "TEST_SETTING") == (
        "configured-value"
    )


@pytest.mark.parametrize("value", [None, "", "   "])
def test_require_value_rejects_missing_value(value):
    with pytest.raises(
        ValueError,
        match="Required LLM configuration is missing: TEST_SETTING",
    ):
        _require_value(value, "TEST_SETTING")


def test_create_llm_rejects_missing_openrouter_api_key():
    settings = type(
        "SettingsStub",
        (),
        {
            "llm_provider": "openrouter",
            "openrouter_api_key": None,
            "openrouter_model": "test-model",
            "openrouter_base_url": "https://openrouter.ai/api/v1",
        },
    )()

    with patch(
        "trialiq.llm.factory.get_settings",
        return_value=settings,
    ):
        with pytest.raises(
            ValueError,
            match="OPENROUTER_API_KEY",
        ):
            create_llm()


def test_create_llm_rejects_missing_openrouter_model():
    settings = type(
        "SettingsStub",
        (),
        {
            "llm_provider": "openrouter",
            "openrouter_api_key": "test-key",
            "openrouter_model": None,
            "openrouter_base_url": "https://openrouter.ai/api/v1",
        },
    )()

    with patch(
        "trialiq.llm.factory.get_settings",
        return_value=settings,
    ):
        with pytest.raises(
            ValueError,
            match="OPENROUTER_MODEL",
        ):
            create_llm()


def test_create_llm_rejects_unsupported_provider():
    settings = type(
        "SettingsStub",
        (),
        {
            "llm_provider": "unsupported-provider",
        },
    )()

    with patch(
        "trialiq.llm.factory.get_settings",
        return_value=settings,
    ):
        with pytest.raises(
            ValueError,
            match="Unsupported LLM provider configured",
        ):
            create_llm()


# Change End