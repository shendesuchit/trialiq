"""Compatibility helpers over TrialIQ's provider-agnostic LLM service."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from trialiq.llm.service import get_llm_service


def get_configured_llm() -> BaseChatModel:
    """Return the currently selected raw LangChain client for legacy injection paths."""
    service = get_llm_service()
    status = service.status()
    if not status.healthy:
        status = service.preflight(probe=False)
    if not status.selected_provider:
        raise ValueError("No configured LLM provider is available.")
    adapter = service.adapter_factory(service.settings, status.selected_provider)
    client = getattr(adapter, "client", None)
    if client is None:
        raise TypeError("Selected LLM provider does not expose a LangChain client.")
    return client


def invoke_llm(question: str, llm: BaseChatModel | None = None):
    """Invoke one text generation call while preserving deterministic injection."""
    if not question or not question.strip():
        raise ValueError("LLM question cannot be empty.")
    if llm is not None:
        return llm.invoke([HumanMessage(content=question)])

    response = get_llm_service().invoke_text([HumanMessage(content=question)])
    return AIMessage(
        content=response.text,
        additional_kwargs={"trialiq_llm_metadata": response.metadata.model_dump()},
    )
