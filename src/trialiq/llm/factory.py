
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from trialiq.config.settings import get_settings


# Change Start
def _require_value(value: str | None, setting_name: str) -> str:
    """Return a required configuration value or raise a safe error."""
    if not value or not value.strip():
        raise ValueError(
            f"Required LLM configuration is missing: {setting_name}"
        )
    return value


def create_llm() -> BaseChatModel:
    """Create the configured LangChain chat model.

    Provider selection is explicit through LLM_PROVIDER.
    """

    settings = get_settings()
    provider = settings.llm_provider

    if provider == "openrouter":
        api_key = _require_value(
            settings.openrouter_api_key,
            "OPENROUTER_API_KEY",
        )
        model = _require_value(
            settings.openrouter_model,
            "OPENROUTER_MODEL",
        )

        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=settings.openrouter_base_url,
            temperature=0,
        )

    if provider == "openai":
        api_key = _require_value(
            settings.openai_api_key,
            "OPENAI_API_KEY",
        )
        model = _require_value(
            settings.openai_model,
            "OPENAI_MODEL",
        )

        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0,
        )

    if provider == "gemini":
        api_key = _require_value(
            settings.gemini_api_key,
            "GEMINI_API_KEY",
        )
        model = _require_value(
            settings.gemini_model,
            "GEMINI_MODEL",
        )

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0,
        )

    if provider == "groq":
        api_key = _require_value(
            settings.groq_api_key,
            "GROQ_API_KEY",
        )
        model = _require_value(
            settings.groq_model,
            "GROQ_MODEL",
        )

        return ChatGroq(
            model=model,
            api_key=api_key,
            temperature=0,
        )

    raise ValueError(
        f"Unsupported LLM provider configured: {provider}"
    )
# Change End