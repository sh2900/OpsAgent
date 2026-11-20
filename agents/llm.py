
import logging
from functools import lru_cache

from backend.config import settings

log = logging.getLogger(__name__)


def _detect_best_gemini_model(api_key: str, requested: str | None = None) -> str:
    """
    Dynamically discover which Gemini model is active on this API key.
    Eliminates all 404 NOT_FOUND errors caused by Google model deprecations.
    """
    candidates = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-flash-latest",
        "gemini-1.5-pro",
    ]
    if requested and "gemini" in requested.lower() and requested not in candidates:
        candidates.insert(0, requested.strip())

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        available = set()
        for m in client.models.list():
            if m.name:
                available.add(m.name)
                available.add(m.name.split("/")[-1])

        for c in candidates:
            if c in available or f"models/{c}" in available:
                print(f"[Gemini Discovery] Selected verified active model: {c}")
                return c

        for m in available:
            if "flash" in m.lower():
                picked = m.split("/")[-1]
                print(f"[Gemini Discovery] Fallback to available flash model: {picked}")
                return picked

    except Exception as e:
        print(f"[Gemini Discovery] Model list check: {e}")

    # Fallback to current release
    return "gemini-2.5-flash"


@lru_cache(maxsize=1)
def get_llm():
    """Create and reuse one chat model based on the configured provider."""

    provider = settings.llm_provider.lower().strip()
    model = settings.llm_model

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is missing from environment")

        gemini_model = _detect_best_gemini_model(settings.google_api_key, model)

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
