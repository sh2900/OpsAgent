from pymongo import MongoClient
from langchain_google_genai import ChatGoogleGenerativeAI
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


def test_gemini():
    assert settings.google_api_key, "Google API key is missing!"

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        api_key=settings.google_api_key,
        temperature=0
    )

    response = llm.invoke(
        "Reply with exactly one word: pong"
    )

    response_text = str(response.content)

    print("\nGemini response:", response_text)

    assert "pong" in response_text.lower()