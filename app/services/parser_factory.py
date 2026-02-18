from enum import Enum

from app.services.base_llm import BaseLLMClient


class ParsingStrategy(str, Enum):
    REGEX = "regex"
    LLM = "llm"
    HYBRID = "hybrid"


class OCRBackend(str, Enum):
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    UNSTRUCTURED = "unstructured"


class LLMModel(str, Enum):
    GROQ_QWEN3 = "qwen/qwen3-32b"
    GROQ_GPT = "openai/gpt-oss-120b"


# Strategies that take raw pdf_bytes (they handle extraction internally)
PDF_BYTES_STRATEGIES = {ParsingStrategy.HYBRID}


def get_llm_client(model: LLMModel) -> BaseLLMClient:
    """Instantiate the Groq LLM client for the given model."""
    from app.services.groq_client import GroqLLMClient
    return GroqLLMClient(model.value)


def get_parser(
    strategy: ParsingStrategy,
    *,
    llm_client: BaseLLMClient | None = None,
):
    """Return the parser for the given strategy.

    Args:
        strategy: Parsing strategy to use.
        llm_client: LLM client to inject into LLM/hybrid parsers.
                    When None, defaults to Groq qwen/qwen3-32b.
    """
    if strategy == ParsingStrategy.REGEX:
        from app.services.receipt_parser import RegexReceiptParser
        return RegexReceiptParser()

    if strategy == ParsingStrategy.LLM:
        from app.services.llm_parser import LlmReceiptParser
        return LlmReceiptParser(llm_client=llm_client)

    if strategy == ParsingStrategy.HYBRID:
        from app.services.hybrid_parser import HybridReceiptParser
        return HybridReceiptParser(llm_client=llm_client)

    raise ValueError(f"Unknown strategy: {strategy}")
