CATEGORY_MAP = {
    "Technical SEO": "Technical SEO",
    "On-Page SEO": "On-Page SEO",
    "Content": "Content",
    "Images": "Image SEO",
    "Social SEO": "Social SEO",
    "Security": "Security",
    "Mobile": "Mobile SEO",
}


def calculate_score(results):
    if not results:
        return 0

    total_checks = len(results)

    passed = sum(
        1
        for result in results
        if result.get("severity") == "Passed"
    )

    warnings = sum(
        1
        for result in results
        if result.get("severity") == "Warning"
    )

    critical = sum(
        1
        for result in results
        if result.get("severity") == "Critical"
    )

    # Weighted score
    weighted_points = (
        passed * 1.0
        + warnings * 0.45
        + critical * 0.0
    )

    score = int(
        (weighted_points / total_checks) * 100
    )

    return max(0, min(100, score))


def score_label(score):

    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Good"

    if score >= 50:
        return "Needs Improvement"

    return "Poor"


def calculate_category_scores(results):

    categories = {}

    for result in results:

        original_category = result.get(
            "category",
            "Other"
        )

        category = CATEGORY_MAP.get(
            original_category,
            original_category
        )

        if category not in categories:
            categories[category] = []

        categories[category].append(result)

    category_scores = {}

    for category, items in categories.items():

        total = len(items)

        passed = sum(
            1
            for item in items
            if item.get("severity") == "Passed"
        )

        warnings = sum(
            1
            for item in items
            if item.get("severity") == "Warning"
        )

        critical = sum(
            1
            for item in items
            if item.get("severity") == "Critical"
        )

        if total:

            weighted = (
                passed * 1.0
                + warnings * 0.45
                + critical * 0.0
            )

            category_score = int(
                (weighted / total) * 100
            )

        else:
            category_score = 0

        category_scores[category] = category_score

    return category_scores


def get_score_status(score):

    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Good"

    if score >= 50:
        return "Needs Improvement"

    return "Poor"
