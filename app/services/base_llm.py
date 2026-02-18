from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Common interface for all LLM backends (Ollama, Groq, etc.)."""

    @abstractmethod
    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        """Send a system + user message and return the assistant's reply.

        Args:
            system_prompt: System instruction (role, format, examples).
            user_prompt: The actual receipt text / data.
            temperature: Sampling temperature (low = deterministic).

        Returns:
            The assistant's reply as a plain string.
        """
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable identifier for logging."""
        ...
