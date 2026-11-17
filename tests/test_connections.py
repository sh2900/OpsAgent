
import pytest
from pymongo import MongoClient

from backend.config import settings


def test_mongo():
    client = MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=10000
    )

    try:
        result = client.admin.command("ping")
        assert result["ok"] == 1.0
        print("\nMongoDB connection successful!")

    finally:
        client.close()


def test_configured_llm():
    """Test the LLM provider configured in .env."""

    provider = settings.llm_provider.lower().strip()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model=settings.llm_model,
            temperature=0,
            reasoning=False
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        assert settings.google_api_key, "Google API key is missing!"

        llm = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0
        )

    elif provider == "groq":
        from langchain_groq import ChatGroq

        assert settings.groq_api_key, "Groq API key is missing!"

        llm = ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            temperature=0
        )

    else:
        pytest.fail(f"Unsupported LLM provider: {provider}")

    response = llm.invoke(
        "Reply with exactly one word: pong"
    )

    response_text = str(response.content)

    print(f"\n{provider.upper()} response:", response_text)

    assert "pong" in response_text.lower()
