# Change Start: Add LLM integration tests

from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage

from trialiq.llm.integration import invoke_llm


def test_invoke_llm_with_injected_model():
    mock_llm = Mock()
    mock_llm.invoke.return_value = AIMessage(
        content="Mock response"
    )

    response = invoke_llm(
        question="Provide a trial overview.",
        llm=mock_llm,
    )

    assert response.content == "Mock response"
    mock_llm.invoke.assert_called_once()


def test_invoke_llm_rejects_empty_question():
    mock_llm = Mock()

    with pytest.raises(ValueError, match="cannot be empty"):
        invoke_llm(
            question="",
            llm=mock_llm,
        )

    mock_llm.invoke.assert_not_called()


def test_invoke_llm_rejects_whitespace_question():
    mock_llm = Mock()

    with pytest.raises(ValueError, match="cannot be empty"):
        invoke_llm(
            question="   ",
            llm=mock_llm,
        )

    mock_llm.invoke.assert_not_called()

# Change End