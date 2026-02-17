from dataclasses import dataclass, field


@dataclass
class FieldScore:
    exact_match: bool
    similarity: float  # 0.0 to 1.0


@dataclass
class ReceiptScore:
    provider_name: FieldScore
    provider_address: FieldScore
    vat_number: FieldScore
    currency: FieldScore
    total_amount: FieldScore
    vat: FieldScore
    items_precision: float
    items_recall: float
    items_f1: float


def score_receipt(predicted: dict, ground_truth: dict) -> ReceiptScore:
    """Compare predicted vs ground truth and return field-level scores."""
    pred_sp = predicted.get("ServiceProvider", {})
    gt_sp = ground_truth.get("ServiceProvider", {})
    pred_td = predicted.get("TransactionDetails", {})
    gt_td = ground_truth.get("TransactionDetails", {})

    provider_name = string_similarity_score(pred_sp.get("Name"), gt_sp.get("Name"))
    provider_address = string_similarity_score(pred_sp.get("Address"), gt_sp.get("Address"))
    vat_number = string_similarity_score(pred_sp.get("VATNumber"), gt_sp.get("VATNumber"))
    currency = exact_match_score(pred_td.get("Currency"), gt_td.get("Currency"))
    total_amount = numeric_match(pred_td.get("TotalAmount"), gt_td.get("TotalAmount"))
    vat = string_similarity_score(pred_td.get("VAT"), gt_td.get("VAT"))

    precision, recall, f1 = score_items(
        pred_td.get("Items", []),
        gt_td.get("Items", []),
    )

    return ReceiptScore(
        provider_name=provider_name,
        provider_address=provider_address,
        vat_number=vat_number,
        currency=currency,
        total_amount=total_amount,
        vat=vat,
        items_precision=precision,
        items_recall=recall,
        items_f1=f1,
    )


def string_similarity_score(a: str | None, b: str | None) -> FieldScore:
    """Compute token-level overlap similarity between two strings."""
    sim = _token_similarity(a, b)
    return FieldScore(exact_match=(a == b), similarity=sim)


def exact_match_score(a: str | None, b: str | None) -> FieldScore:
    """Exact string match scoring."""
    match = _normalize(a) == _normalize(b)
    return FieldScore(exact_match=match, similarity=1.0 if match else 0.0)


def numeric_match(a: float | None, b: float | None, tolerance: float = 0.01) -> FieldScore:
    """Compare numeric fields with a tolerance."""
    if a is None and b is None:
        return FieldScore(exact_match=True, similarity=1.0)
    if a is None or b is None:
        return FieldScore(exact_match=False, similarity=0.0)
    diff = abs(a - b)
    match = diff <= tolerance
    sim = max(0.0, 1.0 - diff / max(abs(b), 1.0))
    return FieldScore(exact_match=match, similarity=sim)


def score_items(
    predicted_items: list[dict], gt_items: list[dict]
) -> tuple[float, float, float]:
    """Compute precision, recall, F1 for item extraction."""
    if not gt_items and not predicted_items:
        return 1.0, 1.0, 1.0
    if not gt_items:
        return 0.0, 1.0, 0.0
    if not predicted_items:
        return 1.0, 0.0, 0.0

    matched_gt = set()
    true_positives = 0

    for pred in predicted_items:
        best_sim = 0.0
        best_idx = -1
        for i, gt in enumerate(gt_items):
            if i in matched_gt:
                continue
            name_sim = _token_similarity(pred.get("Item", ""), gt.get("Item", ""))
            price_ok = abs(pred.get("Price", 0) - gt.get("Price", 0)) <= 0.01
            combined = name_sim * (1.0 if price_ok else 0.5)
            if combined > best_sim:
                best_sim = combined
                best_idx = i

        if best_sim >= 0.4 and best_idx >= 0:
            true_positives += 1
            matched_gt.add(best_idx)

    precision = true_positives / len(predicted_items) if predicted_items else 0.0
    recall = true_positives / len(gt_items) if gt_items else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def _token_similarity(a: str | None, b: str | None) -> float:
    """Normalized token-level overlap between two strings."""
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.0
    tokens_a = set(_normalize(a).split())
    tokens_b = set(_normalize(b).split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _normalize(s: str | None) -> str:
    if s is None:
        return ""
    return s.strip().lower()
