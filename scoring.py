SEVERITY_POINTS = {
    "Critical": -10,
    "Warning": -4,
    "Passed": 2
}


def calculate_score(results):
    if not results:
        return 0

    score = 100

    for result in results:
        severity = result.get("severity")

        if severity == "Critical":
            score -= 8
        elif severity == "Warning":
            score -= 3

    return max(0, min(100, score))


def score_label(score):

    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Needs Improvement"
    else:
        return "Poor"