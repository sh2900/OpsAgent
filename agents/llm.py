
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from backend.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """Create and reuse one Gemini client for all agents."""

    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=0,
    )
