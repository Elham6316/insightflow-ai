import truststore

truststore.inject_into_ssl()

from google import genai

from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)

MODEL_NAME = "models/gemini-3.1-flash-lite"


def test_llm() -> None:
    response = client.models.generate_content(model=MODEL_NAME, contents="say hello")
    print(response.text)


if __name__ == "__main__":
    test_llm()
