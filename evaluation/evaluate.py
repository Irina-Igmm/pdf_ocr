"""
Evaluation pipeline for comparing receipt parsing strategies.

Usage:
    python -m evaluation.evaluate --strategy regex
    python -m evaluation.evaluate --strategy llm
    python -m evaluation.evaluate --strategy gemini
    python -m evaluation.evaluate --strategy hybrid
    python -m evaluation.evaluate --strategy native
    python -m evaluation.evaluate --strategy all
"""

import argparse
import json
import time
from pathlib import Path

from app.services.ocr_engine import extract_text
from app.services.parser_factory import (
    IMAGE_STRATEGIES,
    PDF_BYTES_STRATEGIES,
    ParsingStrategy,
    get_parser,
)
from app.services.pdf_converter import pdf_to_images
from evaluation.metrics import ReceiptScore, score_receipt


def load_ground_truth(gt_dir: Path) -> list[dict]:
    labels = []
    for f in sorted(gt_dir.glob("*.json")):
        labels.append(json.loads(f.read_text(encoding="utf-8")))
    return labels


def evaluate_strategy(
    strategy: ParsingStrategy, labels: list[dict]
) -> list[dict]:
    parser = get_parser(strategy)
    is_image_strategy = strategy in IMAGE_STRATEGIES
    is_pdf_bytes_strategy = strategy in PDF_BYTES_STRATEGIES
    results = []

    for label in labels:
        pdf_path = Path(label["pdf_path"])
        if not pdf_path.exists():
            print(f"  [SKIP] {pdf_path} not found")
            continue

        pdf_bytes = pdf_path.read_bytes()

        start = time.time()

        if is_pdf_bytes_strategy:
            prediction = parser.parse(pdf_bytes)
        elif is_image_strategy:
            images = pdf_to_images(pdf_bytes)
            prediction = parser.parse(images)
        else:
            images = pdf_to_images(pdf_bytes)
            raw_text = extract_text(images)
            prediction = parser.parse(raw_text)

        elapsed = time.time() - start

        pred_dict = prediction.model_dump(by_alias=True)
        score = score_receipt(pred_dict, label["ground_truth"])

        results.append(
            {
                "pdf": label["pdf_path"],
                "strategy": strategy.value,
                "time_seconds": round(elapsed, 2),
                "score": score,
                "prediction": pred_dict,
            }
        )
        print(f"  [{strategy.value}] {pdf_path.name} — {elapsed:.1f}s")

    return results


def print_summary(strategy_name: str, results: list[dict]) -> None:
    if not results:
        print(f"\n  No results for {strategy_name}")
        return

    scores: list[ReceiptScore] = [r["score"] for r in results]
    n = len(scores)

    avg_name = sum(s.provider_name.similarity for s in scores) / n
    avg_addr = sum(s.provider_address.similarity for s in scores) / n
    avg_vat_num = sum(s.vat_number.similarity for s in scores) / n
    avg_currency = sum(s.currency.similarity for s in scores) / n
    avg_total = sum(s.total_amount.similarity for s in scores) / n
    avg_vat = sum(s.vat.similarity for s in scores) / n
    avg_items_f1 = sum(s.items_f1 for s in scores) / n
    avg_time = sum(r["time_seconds"] for r in results) / n

    print(f"\n{'=' * 55}")
    print(f"  Strategy: {strategy_name.upper()} ({n} receipts)")
    print(f"{'=' * 55}")
    print(f"  {'Field':<25} {'Avg Similarity':>15}")
    print(f"  {'-' * 40}")
    print(f"  {'Provider Name':<25} {avg_name:>14.1%}")
    print(f"  {'Provider Address':<25} {avg_addr:>14.1%}")
    print(f"  {'VAT Number':<25} {avg_vat_num:>14.1%}")
    print(f"  {'Currency':<25} {avg_currency:>14.1%}")
    print(f"  {'Total Amount':<25} {avg_total:>14.1%}")
    print(f"  {'VAT Info':<25} {avg_vat:>14.1%}")
    print(f"  {'Items F1':<25} {avg_items_f1:>14.1%}")
    print(f"  {'-' * 40}")
    print(f"  {'Avg Latency':<25} {avg_time:>13.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate receipt parsing strategies"
    )
    parser.add_argument(
        "--strategy",
        choices=["regex", "llm", "gemini", "hybrid", "native", "all"],
        default="all",
    )
    parser.add_argument(
        "--gt-dir",
        default="evaluation/ground_truth",
        help="Path to ground truth directory",
    )
    args = parser.parse_args()

    gt_dir = Path(args.gt_dir)
    labels = load_ground_truth(gt_dir)
    print(f"Loaded {len(labels)} ground truth labels from {gt_dir}")

    all_strategies = list(ParsingStrategy)

    if args.strategy == "all":
        strategies = all_strategies
    else:
        strategies = [ParsingStrategy(args.strategy)]

    for strategy in strategies:
        print(f"\nEvaluating strategy: {strategy.value}")
        results = evaluate_strategy(strategy, labels)
        print_summary(strategy.value, results)


if __name__ == "__main__":
    main()
