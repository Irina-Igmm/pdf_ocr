"""Quick smoke-test: verify the Ollama connection works."""

from app.services.ollama_client import chat_completion


def test_ollama_connection():
    response = chat_completion(
        system_prompt="You are a helpful assistant.",
        user_prompt="Reply with exactly: OK",
    )
    print("Ollama response:", response)
    assert "OK" in response.upper()


if __name__ == "__main__":
    test_ollama_connection()