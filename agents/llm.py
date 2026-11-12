
from functools import lru_cache

from backend.config import settings


@lru_cache(maxsize=1)
def get_llm():
    """Create and reuse one chat model based on the configured provider."""

    provider = settings.llm_provider.lower().strip()
    model = settings.llm_model

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is missing from .env")

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=0,
        )

    elif provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing from .env")

        return ChatGroq(
            model=model,
            api_key=settings.groq_api_key,
            temperature=0,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            temperature=0,
	    reasoning=False,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            "Choose gemini, groq, or ollama."
        )
