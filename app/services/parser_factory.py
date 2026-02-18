from enum import Enum


class ParsingStrategy(str, Enum):
    REGEX = "regex"
    LLM = "llm"
    HYBRID = "hybrid"


# Strategies that take raw pdf_bytes (they handle extraction internally)
PDF_BYTES_STRATEGIES = {ParsingStrategy.HYBRID}


def get_parser(strategy: ParsingStrategy):
    if strategy == ParsingStrategy.REGEX:
        from app.services.receipt_parser import RegexReceiptParser

        return RegexReceiptParser()

    if strategy == ParsingStrategy.LLM:
        from app.services.llm_parser import LlmReceiptParser

        return LlmReceiptParser()

    if strategy == ParsingStrategy.HYBRID:
        from app.services.hybrid_parser import HybridReceiptParser

        return HybridReceiptParser()

    raise ValueError(f"Unknown strategy: {strategy}")
