
from functools import lru_cache

from backend.config import settings


@lru_cache(maxsize=1)
def get_llm():
    """Create and reuse one chat model based on the configured provider."""

    provider = settings.llm_provider.lower().strip()
    model = settings.llm_model

    if provider == "gemini":
        import os
        os.environ["GOOGLE_GENAI_API_VERSION"] = "v1beta"
        os.environ["GOOGLE_API_VERSION"] = "v1beta"
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is missing from environment")

        # Always use active gemini-2.0-flash (automatically replaces deprecated gemini-1.5-flash)
        gemini_model = "gemini-2.0-flash"
        if model and ("2.0" in model or "2.5" in model):
            gemini_model = model.strip()

        return ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0,
        )

    elif provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing from environment")

        groq_model = (
            model
            if model and ("llama" in model.lower() or "mixtral" in model.lower() or "gemma" in model.lower())
            else "llama-3.1-8b-instant"
        )

        return ChatGroq(
            model=groq_model,
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
