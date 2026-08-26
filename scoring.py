CATEGORY_ORDER = ["On-Page SEO", "Content", "Image SEO", "Technical SEO", "Mobile SEO", "Social SEO", "Security"]


def _score(items):
    if not items:
        return 100
    weights = {"Critical": 0, "Warning": 55, "Passed": 100}
    return round(sum(weights.get(str(x.get("severity", "Warning")), 55) for x in items) / len(items))


def calculate_category_scores(results):
    grouped = {name: [] for name in CATEGORY_ORDER}
    for item in results or []:
        category = str(item.get("category") or "Other")
        if category in grouped:
            grouped[category].append(item)
    return {name: _score(items) for name, items in grouped.items() if items}


def calculate_score(results):
    scores = calculate_category_scores(results)
    if not scores:
        return 0
    return round(sum(scores.values()) / len(scores))


def score_label(score):
    try:
        score = float(score)
    except Exception:
        return "Unknown"
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    return "Poor"
