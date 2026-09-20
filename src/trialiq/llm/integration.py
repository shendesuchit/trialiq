# Change Start: Add LLM integration boundary

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from trialiq.llm.factory import create_llm


def get_configured_llm() -> BaseChatModel:
    """Return the configured LLM through the provider factory."""
    return create_llm()


def invoke_llm(
    question: str,
    llm: BaseChatModel | None = None,
) -> BaseMessage:
    """Invoke an LLM with an explicit question.

    The LLM is injected when supplied, allowing deterministic testing.
    No fallback clinical answer is generated when invocation fails.
    """

    if not question or not question.strip():
        raise ValueError("LLM question cannot be empty.")

    configured_llm = llm or get_configured_llm()

    return configured_llm.invoke(
        [HumanMessage(content=question)]
    )


# Change End