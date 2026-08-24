import streamlit as st
import pandas as pd
from collections import defaultdict
from io import BytesIO
from datetime import datetime

from modules.crawler import crawl_website, normalize_url
from modules.seo_audit import (
    audit_page,
    audit_links,
    robots_and_sitemap,
)
from modules.scoring import (
    calculate_score,
    score_label,
    calculate_category_scores,
)
from reports.pdf_report import build_pdf_report

# Excel module
try:
    from reports.excel_report import build_excel_report
    EXCEL_AVAILABLE = True
except Exception:
    EXCEL_AVAILABLE = False


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Agency SEO Auditor",
    page_icon="🔎",
    layout="wide",
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
<style>

.main {
    background: #f8fafc;
}

.block-container {
    max-width: 1400px;
    padding-top: 2rem;
}

h1, h2, h3 {
    color: #172554;
}

.hero {
    background: linear-gradient(
        135deg,
        #172554,
        #1d4ed8
    );
    padding: 32px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 10px 30px rgba(15,23,42,.15);
}

.hero h1 {
    color: white;
    margin-bottom: 5px;
}

.hero p {
    color: #dbeafe;
    font-size: 16px;
}

.section-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 18px;
    box-shadow: 0 4px 15px rgba(15,23,42,.05);
}

.score-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 25px;
    text-align: center;
    box-shadow: 0 5px 20px rgba(15,23,42,.06);
}

.score-number {
    font-size: 58px;
    font-weight: 800;
    color: #2563eb;
}

.score-status {
    font-size: 20px;
    font-weight: 700;
    color: #475569;
}

.metric-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 15px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(15,23,42,.04);
}

.metric-number {
    font-size: 30px;
    font-weight: 800;
}

.metric-label {
    color: #64748b;
    font-size: 14px;
    margin-top: 5px;
}

.category-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 12px;
}

.category-name {
    font-weight: 700;
    color: #172554;
}

.category-number {
    font-size: 24px;
    font-weight: 800;
    color: #2563eb;
}

.issue-card {
    background: white;
    border-radius: 14px;
    padding: 18px;
    margin: 10px 0;
    border-left: 5px solid #f59e0b;
    box-shadow: 0 3px 12px rgba(15,23,42,.06);
}

.issue-critical {
    border-left-color: #dc2626;
}

.issue-warning {
    border-left-color: #f59e0b;
}

.issue-passed {
    border-left-color: #16a34a;
}

.issue-title {
    font-weight: 750;
    font-size: 16px;
    color: #172554;
}

.issue-meta {
    color: #64748b;
    font-size: 13px;
    margin-top: 6px;
}

.issue-fix {
    margin-top: 10px;
    color: #334155;
    font-size: 14px;
}

.action-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 17px;
    margin: 9px 0;
}

.action-number {
    display: inline-block;
    background: #2563eb;
    color: white;
    width: 28px;
    height: 28px;
    text-align: center;
    line-height: 28px;
    border-radius: 50%;
    margin-right: 8px;
    font-weight: 700;
}

.small-muted {
    color: #64748b;
    font-size: 13px;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================

def safe_value(value, default=""):
    if value is None:
        return default

    if isinstance(value, float) and pd.isna(value):
        return default

    return value


def normalize_category(category):
    category = str(category or "Other").strip()

    mapping = {
        "technical": "Technical SEO",
        "technical seo": "Technical SEO",
        "on-page": "On-Page SEO",
        "on-page seo": "On-Page SEO",
        "content": "Content",
        "image": "Image SEO",
        "image seo": "Image SEO",
        "images": "Image SEO",
        "social": "Social SEO",
        "social seo": "Social SEO",
        "security": "Security",
        "mobile": "Mobile SEO",
        "mobile seo": "Mobile SEO",
    }

    return mapping.get(
        category.lower(),
        category,
    )


def get_result_url(result):
    """
    Try all common URL field names.
    """

    possible = [
        "url",
        "URL",
        "page_url",
        "pageUrl",
        "page",
        "Page",
        "source_url",
        "source",
    ]

    for key in possible:
        value = result.get(key)

        if value:
            return str(value).strip()

    return ""


def attach_page_url(results, page_url):
    """
    Guarantees every audit result has a page URL.
    """

    fixed = []

    for result in results:

        if not isinstance(result, dict):
            continue

        item = dict(result)

        if not get_result_url(item):
            item["url"] = page_url

        fixed.append(item)

    return fixed


def aggregate_issues(results):
    """
    Creates client-friendly aggregated findings while
    preserving affected URLs.
    """

    groups = {}

    for result in results:

        category = normalize_category(
            result.get(
                "category",
                "Other",
            )
        )

        severity = str(
            result.get(
                "severity",
                "Warning",
            )
        ).strip()

        issue = str(
            result.get(
                "issue",
                result.get(
                    "message",
                    "SEO issue",
                ),
            )
        ).strip()

        recommendation = str(
            result.get(
                "recommendation",
                result.get(
                    "fix",
                    "Review and fix this issue.",
                ),
            )
        ).strip()

        url = get_result_url(result)

        lower = issue.lower()

        if "missing alt text" in lower:
            issue_key = "missing_alt_text"

        elif (
            "security header" in lower
            and "missing" in lower
        ):
            issue_key = "missing_security_headers"

        elif (
            "meta description" in lower
            and "missing" in lower
        ):
            issue_key = "missing_meta_description"

        elif "title tag is too short" in lower:
            issue_key = "short_title"

        elif "title tag may be too long" in lower:
            issue_key = "long_title"

        elif (
            "meta description may be too long"
            in lower
        ):
            issue_key = "long_meta_description"

        elif "open graph" in lower:
            issue_key = "incomplete_open_graph"

        elif "multiple h1" in lower:
            issue_key = "multiple_h1"

        else:
            issue_key = lower

        group_key = (
            category,
            severity,
            issue_key,
        )

        if group_key not in groups:

            groups[group_key] = {
                "category": category,
                "severity": severity,
                "issue_key": issue_key,
                "recommendation": recommendation,
                "occurrences": 0,
                "pages": set(),
                "numeric_values": [],
            }

        group = groups[group_key]

        group["occurrences"] += 1

        if url:
            group["pages"].add(url)

        # Extract numeric count from issue text.
        import re

        numbers = re.findall(
            r"\b\d+\b",
            issue,
        )

        for number in numbers:

            try:
                group["numeric_values"].append(
                    int(number)
                )
            except Exception:
                pass

    aggregated = []

    for group in groups.values():

        key = group["issue_key"]

        numeric_total = sum(
            group["numeric_values"]
        )

        if key == "missing_alt_text":

            if numeric_total > 0:
                title = (
                    f"{numeric_total} image"
                    f"{'s' if numeric_total != 1 else ''} "
                    "missing alt text"
                )
            else:
                title = "Images missing alt text"

        elif key == "missing_security_headers":

            if numeric_total > 0:
                title = (
                    f"{numeric_total} recommended security "
                    f"header{'s' if numeric_total != 1 else ''} missing"
                )
            else:
                title = (
                    "Recommended security headers missing"
                )

        elif key == "missing_meta_description":
            title = "Missing meta description"

        elif key == "short_title":
            title = "Title tag is too short"

        elif key == "long_title":
            title = "Title tag may be too long"

        elif key == "long_meta_description":
            title = (
                "Meta description may be too long"
            )

        elif key == "incomplete_open_graph":
            title = (
                "Incomplete Open Graph metadata"
            )

        elif key == "multiple_h1":
            title = "Multiple H1 headings"

        else:

            title = (
                group["issue_key"]
                .replace("_", " ")
                .capitalize()
            )

        pages = sorted(
            group["pages"]
        )

        aggregated.append(
            {
                "category": group["category"],
                "severity": group["severity"],
                "issue": title,
                "recommendation": group["recommendation"],
                "occurrences": group["occurrences"],
                "affected_pages": len(pages),
                "pages": pages,
            }
        )

    priority = {
        "Critical": 0,
        "Warning": 1,
        "Passed": 2,
    }

    aggregated.sort(
        key=lambda x: (
            priority.get(
                x["severity"],
                3,
            ),
            -x["occurrences"],
        )
    )

    return aggregated


def result_dataframe(results):
    """
    Clean detailed findings dataframe.
    """

    rows = []

    for result in results:

        rows.append(
            {
                "Severity": safe_value(
                    result.get("severity")
                ),
                "Category": normalize_category(
                    result.get(
                        "category",
                        "Other",
                    )
                ),
                "Issue": safe_value(
                    result.get("issue")
                    or result.get("message")
                ),
                "Recommended Fix": safe_value(
                    result.get(
                        "recommendation"
                    )
                    or result.get("fix")
                ),
                "Page / URL": get_result_url(
                    result
                ),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    order = {
        "Critical": 0,
        "Warning": 1,
        "Passed": 2,
    }

    df["_order"] = (
        df["Severity"]
        .map(order)
        .fillna(3)
    )

    df = df.sort_values(
        "_order"
    ).drop(
        columns="_order"
    )

    return df


def get_action_plan(aggregated):
    """
    Critical issues first, then warnings.
    """

    critical = [
        item
        for item in aggregated
        if item["severity"] == "Critical"
    ]

    warnings = [
        item
        for item in aggregated
        if item["severity"] == "Warning"
    ]

    return (
        critical + warnings
    )[:6]


def status_for_category(score):
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


def flatten_pages(crawled_pages):
    """
    Convert crawler output into a clean list.
    """

    output = []

    if isinstance(
        crawled_pages,
        dict,
    ):
        iterable = list(
            crawled_pages.values()
        )
    else:
        iterable = crawled_pages or []

    for page in iterable:

        if isinstance(page, str):

            output.append(
                {
                    "URL": page,
                    "Status": "",
                    "Title": "",
                    "Issues": "",
                }
            )

            continue

        if not isinstance(page, dict):
            continue

        output.append(
            {
                "URL": (
                    page.get("url")
                    or page.get("URL")
                    or ""
                ),
                "Status": (
                    page.get("status")
                    or page.get("Status")
                    or page.get("status_code")
                    or ""
                ),
                "Title": (
                    page.get("title")
                    or page.get("Title")
                    or ""
                ),
                "Issues": (
                    page.get("issues")
                    or page.get("Issues")
                    or 0
                ),
            }
        )

    return output


def clean_broken_links(data):
    if data is None:
        return []

    if isinstance(data, pd.DataFrame):
        return data.to_dict(
            orient="records"
        )

    if isinstance(data, list):
        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    if isinstance(data, dict):
        return [data]

    return []


def clean_technical_data(data):
    """
    Keeps robots/sitemap output safe for Excel.
    """

    if not isinstance(data, dict):
        return {}

    return data


# =========================================================
# SESSION STATE
# =========================================================

if "audit_complete" not in st.session_state:
    st.session_state.audit_complete = False

if "all_results" not in st.session_state:
    st.session_state.all_results = []

if "aggregated" not in st.session_state:
    st.session_state.aggregated = []

if "audit_pages" not in st.session_state:
    st.session_state.audit_pages = []

if "broken_links" not in st.session_state:
    st.session_state.broken_links = []

if "technical_data" not in st.session_state:
    st.session_state.technical_data = {}

if "score" not in st.session_state:
    st.session_state.score = 0

if "score_status" not in st.session_state:
    st.session_state.score_status = ""


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
<div class="hero">

<h1>🔎 Agency SEO Auditor v6.0</h1>

<p>
Professional SEO auditing and client reporting platform
</p>

</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "## 🏢 Agency Profile"
    )

    agency_name = st.text_input(
        "Agency Name",
        placeholder="Your Agency",
    )

    agency_website = st.text_input(
        "Agency Website",
        placeholder="https://youragency.com",
    )

    agency_email = st.text_input(
        "Agency Email",
        placeholder="hello@youragency.com",
    )

    agency_logo = st.file_uploader(
        "Agency Logo",
        type=[
            "png",
            "jpg",
            "jpeg",
        ],
    )

    st.markdown("---")

    st.markdown(
        "## ⚙️ Audit Settings"
    )

    max_pages = st.slider(
        "Pages to crawl",
        min_value=1,
        max_value=30,
        value=10,
    )

    check_broken = st.checkbox(
        "Check broken links",
        value=True,
    )


# =========================================================
# CLIENT INFORMATION
# =========================================================

st.markdown(
    "## 👤 Client Information"
)

client_col1, client_col2 = st.columns(2)

with client_col1:

    client_name = st.text_input(
        "Client / Company Name",
        placeholder="Client Company",
    )

with client_col2:

    client_website = st.text_input(
        "Client Website",
        placeholder="https://client.com",
    )


st.markdown(
    "### 🌐 Website URL to Audit"
)

audit_url = st.text_input(
    "Website URL",
    value=client_website,
    placeholder="https://example.com",
    label_visibility="collapsed",
)


# =========================================================
# START AUDIT
# =========================================================

start_audit = st.button(
    "🚀 Start SEO Audit",
    type="primary",
    use_container_width=True,
)


if start_audit:

    if not audit_url.strip():

        st.error(
            "Please enter a website URL."
        )

        st.stop()

    try:

        normalized_url = normalize_url(
            audit_url.strip()
        )

        progress = st.progress(
            0
        )

        status = st.empty()

        # -------------------------------------------------
        # CRAWL
        # -------------------------------------------------

        status.write(
            "🌐 Crawling website..."
        )

        crawled = crawl_website(
            normalized_url,
            max_pages=max_pages,
        )

        progress.progress(
            25
        )

        # -------------------------------------------------
        # NORMALIZE CRAWLER OUTPUT
        # -------------------------------------------------

        pages_for_audit = []

        if isinstance(
            crawled,
            dict,
        ):

            pages_for_audit = list(
                crawled.values()
            )

        elif isinstance(
            crawled,
            list,
        ):

            pages_for_audit = crawled

        # -------------------------------------------------
        # AUDIT EACH PAGE
        # -------------------------------------------------

        status.write(
            "🔎 Running SEO checks..."
        )

        all_results = []

        for index, page in enumerate(
            pages_for_audit
        ):

            page_url = ""

            if isinstance(
                page,
                str,
            ):

                page_url = page

            elif isinstance(
                page,
                dict,
            ):

                page_url = (
                    page.get("url")
                    or page.get("URL")
                    or ""
                )

            if not page_url:
                continue

            try:

                page_results = audit_page(
                    page
                )

            except Exception:

                try:

                    page_results = audit_page(
                        page_url
                    )

                except Exception:
                    page_results = []

            page_results = attach_page_url(
                page_results,
                page_url,
            )

            all_results.extend(
                page_results
            )

            progress.progress(
                min(
                    25
                    + int(
                        (
                            (index + 1)
                            / max(
                                len(
                                    pages_for_audit
                                ),
                                1,
                            )
                        )
                        * 35
                    ),
                    60,
                )
            )

        # -------------------------------------------------
        # BROKEN LINKS
        # -------------------------------------------------

        broken_links = []

        if check_broken:

            status.write(
                "🔗 Checking links..."
            )

            try:

                link_data = audit_links(
                    pages_for_audit
                )

                broken_links = clean_broken_links(
                    link_data
                )

            except Exception as error:

                st.warning(
                    f"Broken-link check skipped: {error}"
                )

        progress.progress(
            75
        )

        # -------------------------------------------------
        # ROBOTS + SITEMAP
        # -------------------------------------------------

        status.write(
            "⚙️ Checking robots.txt and sitemap..."
        )

        try:

            technical_data = robots_and_sitemap(
                normalized_url
            )

        except Exception:

            technical_data = {}

        progress.progress(
            85
        )

        # -------------------------------------------------
        # SCORE
        # -------------------------------------------------

        status.write(
            "📊 Calculating SEO score..."
        )

        try:

            score = calculate_score(
                all_results
            )

        except Exception:

            score = 0

        try:

            score_text = score_label(
                score
            )

        except Exception:

            score_text = (
                "Good"
                if score >= 75
                else "Needs Improvement"
            )

        # -------------------------------------------------
        # AGGREGATION
        # -------------------------------------------------

        aggregated = aggregate_issues(
            all_results
        )

        # -------------------------------------------------
        # SAVE RESULTS
        # -------------------------------------------------

        st.session_state.audit_complete = True
        st.session_state.all_results = all_results
        st.session_state.aggregated = aggregated
        st.session_state.audit_pages = flatten_pages(
            pages_for_audit
        )
        st.session_state.broken_links = broken_links
        st.session_state.technical_data = clean_technical_data(
            technical_data
        )
        st.session_state.score = score
        st.session_state.score_status = score_text

        progress.progress(
            100
        )

        status.success(
            "✅ SEO audit completed successfully."
        )

    except Exception as error:

        st.error(
            f"Audit failed: {error}"
        )

        st.stop()


# =========================================================
# DASHBOARD
# =========================================================

if st.session_state.audit_complete:

    all_results = (
        st.session_state.all_results
    )

    aggregated = (
        st.session_state.aggregated
    )

    pages = (
        st.session_state.audit_pages
    )

    broken_links = (
        st.session_state.broken_links
    )

    technical_data = (
        st.session_state.technical_data
    )

    score = (
        st.session_state.score
    )

    score_text = (
        st.session_state.score_status
    )

    # -----------------------------------------------------
    # COUNTS
    # -----------------------------------------------------

    critical_count = sum(
        1
        for result in all_results
        if result.get("severity")
        == "Critical"
    )

    warning_count = sum(
        1
        for result in all_results
        if result.get("severity")
        == "Warning"
    )

    passed_count = sum(
        1
        for result in all_results
        if result.get("severity")
        == "Passed"
    )

    # -----------------------------------------------------
    # DASHBOARD
    # -----------------------------------------------------

    st.markdown(
        "## 📊 SEO Performance Dashboard"
    )

    st.info(
        "Client-ready website health overview "
        "and prioritized SEO recommendations."
    )

    st.markdown(
        f"""
### Executive Summary

The website currently has an SEO score of
**{score}/100**, classified as **{score_text}**.

The audit detected **{critical_count}**
critical issues, **{warning_count}**
warnings, and **{passed_count}**
passed checks.
"""
    )

    # -----------------------------------------------------
    # SCORE + METRICS
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
<div class="score-card">

<div>
OVERALL SEO SCORE
</div>

<div class="score-number">
{score}
</div>

<div>
OUT OF 100
</div>

<div class="score-status">
{score_text}
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            f"""
<div class="metric-card">

<div class="metric-number">
🔴 {critical_count}
</div>

<div class="metric-label">
Critical Issues
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    with c3:

        st.markdown(
            f"""
<div class="metric-card">

<div class="metric-number">
🟠 {warning_count}
</div>

<div class="metric-label">
Warnings
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    with c4:

        st.markdown(
            f"""
<div class="metric-card">

<div class="metric-number">
🟢 {passed_count}
</div>

<div class="metric-label">
Passed Checks
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"**Audited website:** `{audit_url}`"
    )

    # -----------------------------------------------------
    # CATEGORY PERFORMANCE
    # -----------------------------------------------------

    st.markdown(
        "## 📈 SEO Category Performance"
    )

    try:

        category_scores = (
            calculate_category_scores(
                all_results
            )
        )

    except Exception:

        category_scores = {}

    if isinstance(
        category_scores,
        dict,
    ):

        category_items = list(
            category_scores.items()
        )

    else:

        category_items = []

    if category_items:

        for start in range(
            0,
            len(category_items),
            3,
        ):

            cols = st.columns(3)

            for col, item in zip(
                cols,
                category_items[
                    start:start + 3
                ],
            ):

                category_name, category_score = item

                with col:

                    try:
                        numeric_score = float(
                            category_score
                        )
                    except Exception:
                        numeric_score = 0

                    category_status = (
                        status_for_category(
                            numeric_score
                        )
                    )

                    st.markdown(
                        f"""
<div class="category-card">

<div class="category-name">
{normalize_category(category_name)}
</div>

<div class="category-number">
{numeric_score:.0f}/100
</div>

<div class="small-muted">
Status: {category_status}
</div>

</div>
""",
                        unsafe_allow_html=True,
                    )


    # -----------------------------------------------------
    # PRIORITIZED FINDINGS
    # -----------------------------------------------------

    st.markdown(
        "## 🚨 Prioritized SEO Findings"
    )

    critical_items = [
        item
        for item in aggregated
        if item["severity"] == "Critical"
    ]

    warning_items = [
        item
        for item in aggregated
        if item["severity"] == "Warning"
    ]

    passed_items = [
        item
        for item in aggregated
        if item["severity"] == "Passed"
    ]

    # -----------------------------------------------------
    # CRITICAL
    # -----------------------------------------------------

    st.markdown(
        "### 🔴 Critical Issues"
    )

    if critical_items:

        for item in critical_items:

            page_count = item[
                "affected_pages"
            ]

            page_word = (
                "page"
                if page_count == 1
                else "pages"
            )

            st.markdown(
                f"""
<div class="issue-card issue-critical">

<div class="issue-title">
🔴 {item["issue"]}
</div>

<div class="issue-meta">
{item["category"]} ·
{item["occurrences"]} occurrence(s) ·
{page_count} affected {page_word}
</div>

<div class="issue-fix">
<b>Recommended Fix:</b>
{item["recommendation"]}
</div>

</div>
""",
                unsafe_allow_html=True,
            )

            if item["pages"]:

                with st.expander(
                    "View affected URLs"
                ):

                    for url in item["pages"]:
                        st.write(
                            f"• {url}"
                        )

    else:

        st.success(
            "No critical issues detected."
        )

    # -----------------------------------------------------
    # WARNINGS
    # -----------------------------------------------------

    st.markdown(
        "### 🟠 Warnings"
    )

    if warning_items:

        for item in warning_items:

            page_count = item[
                "affected_pages"
            ]

            page_word = (
                "page"
                if page_count == 1
                else "pages"
            )

            st.markdown(
                f"""
<div class="issue-card issue-warning">

<div class="issue-title">
🟠 {item["issue"]}
</div>

<div class="issue-meta">
{item["category"]} ·
{item["occurrences"]} occurrence(s) ·
{page_count} affected {page_word}
</div>

<div class="issue-fix">
<b>Recommended Fix:</b>
{item["recommendation"]}
</div>

</div>
""",
                unsafe_allow_html=True,
            )

            if item["pages"]:

                with st.expander(
                    "View affected URLs"
                ):

                    for url in item["pages"]:
                        st.write(
                            f"• {url}"
                        )

    else:

        st.success(
            "No warnings detected."
        )

    # -----------------------------------------------------
    # ACTION PLAN
    # -----------------------------------------------------

    st.markdown(
        "## 🛠️ Recommended Action Plan"
    )

    action_plan = get_action_plan(
        aggregated
    )

    if action_plan:

        for index, action in enumerate(
            action_plan,
            start=1,
        ):

            icon = (
                "🔴"
                if action["severity"]
                == "Critical"
                else "🟠"
            )

            page_count = action[
                "affected_pages"
            ]

            page_word = (
                "page"
                if page_count == 1
                else "pages"
            )

            st.markdown(
                f"""
<div class="action-card">

<span class="action-number">
{index}
</span>

<b>
{icon} {action["issue"]}
</b>

<br>

<small>
{page_count} affected {page_word}
</small>

<br><br>

<small>
<b>Recommended Fix:</b>
{action["recommendation"]}
</small>

</div>
""",
                unsafe_allow_html=True,
            )

    else:

        st.success(
            "No immediate action items detected."
        )


    # =====================================================
    # CLIENT REPORT
    # =====================================================

    st.markdown(
        "## 📄 Client Report"
    )

    st.info(
        "Generate professional white-label "
        "reports for your client."
    )

    # -----------------------------------------------------
    # REPORT DATA
    # -----------------------------------------------------

    report_data = {
        "agency_name": agency_name,
        "agency_website": agency_website,
        "agency_email": agency_email,
        "client_name": client_name,
        "client_website": client_website,
        "audit_url": audit_url,
        "score": score,
        "score_label": score_text,
        "critical": critical_count,
        "warnings": warning_count,
        "passed": passed_count,
        "results": all_results,
        "aggregated": aggregated,
        "pages": pages,
        "broken_links": broken_links,
        "technical": technical_data,
    }

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    try:

        pdf_bytes = build_pdf_report(
            report_data
        )

        st.download_button(
            "📥 Download Professional PDF Report",
            data=pdf_bytes,
            file_name=(
                "SEO_Audit_Report_"
                + (
                    client_name
                    or "Client"
                ).replace(
                    " ",
                    "_",
                )
                + ".pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

    except Exception as error:

        st.warning(
            "PDF report could not be generated "
            "with the current PDF module."
        )

        with st.expander(
            "PDF technical details"
        ):
            st.code(
                str(error)
            )

    # -----------------------------------------------------
    # EXCEL
    # -----------------------------------------------------

    if EXCEL_AVAILABLE:

        try:

            excel_bytes = build_excel_report(
                agency_name=agency_name,
                agency_website=agency_website,
                agency_email=agency_email,
                client_name=client_name or "Client",
                client_website=(
                    client_website
                    or audit_url
                ),
                score=score,
                score_label=score_text,
                results=all_results,
                pages=pages,
                broken_links=broken_links,
                technical_files=technical_data,
            )

            st.download_button(
                "📊 Download Professional Excel Report",
                data=excel_bytes,
                file_name=(
                    "SEO_Audit_Report_"
                    + (
                        client_name
                        or "Client"
                    ).replace(
                        " ",
                        "_",
                    )
                    + ".xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        except Exception as error:

            st.warning(
                "Excel report could not be generated."
            )

            with st.expander(
                "Excel technical details"
            ):
                st.code(
                    str(error)
                )

    else:

        st.warning(
            "Professional Excel module is not installed. "
            "Add reports/excel_report.py to enable it."
        )


    # =====================================================
    # DATA EXPORT
    # =====================================================

    st.markdown(
        "## 📊 Audit Data"
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Audit Results",
            "🌐 Pages",
            "🔗 Broken Links",
            "⚙️ Technical",
        ]
    )

    # -----------------------------------------------------
    # RESULTS
    # -----------------------------------------------------

    with tab1:

        findings_df = result_dataframe(
            all_results
        )

        if findings_df.empty:

            st.info(
                "No audit findings available."
            )

        else:

            severity_filter = st.multiselect(
                "Filter by severity",
                options=[
                    "Critical",
                    "Warning",
                    "Passed",
                ],
                default=[
                    "Critical",
                    "Warning",
                    "Passed",
                ],
            )

            filtered_df = findings_df[
                findings_df["Severity"].isin(
                    severity_filter
                )
            ]

            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True,
            )

            # Clean CSV
            csv_bytes = (
                filtered_df
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8-sig"
                )
            )

            st.download_button(
                "⬇️ Download Clean CSV",
                data=csv_bytes,
                file_name=(
                    "SEO_Audit_Findings.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )

    # -----------------------------------------------------
    # PAGES
    # -----------------------------------------------------

    with tab2:

        if pages:

            pages_df = pd.DataFrame(
                pages
            )

            st.dataframe(
                pages_df,
                use_container_width=True,
                hide_index=True,
            )

            pages_csv = (
                pages_df
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8-sig"
                )
            )

            st.download_button(
                "⬇️ Download Pages CSV",
                data=pages_csv,
                file_name="Crawled_Pages.csv",
                mime="text/csv",
                use_container_width=True,
            )

        else:

            st.info(
                "No crawled pages available."
            )

    # -----------------------------------------------------
    # BROKEN LINKS
    # -----------------------------------------------------

    with tab3:

        if broken_links:

            broken_df = pd.DataFrame(
                broken_links
            )

            st.dataframe(
                broken_df,
                use_container_width=True,
                hide_index=True,
            )

            broken_csv = (
                broken_df
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8-sig"
                )
            )

            st.download_button(
                "⬇️ Download Broken Links CSV",
                data=broken_csv,
                file_name=(
                    "Broken_Links.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )

        else:

            st.success(
                "No broken links detected."
            )

    # -----------------------------------------------------
    # TECHNICAL
    # -----------------------------------------------------

    with tab4:

        if technical_data:

            st.json(
                technical_data
            )

        else:

            st.info(
                "No technical data available."
            )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
<hr>

<div style="
text-align:center;
color:#64748b;
padding:20px;
">

<b>Agency SEO Auditor v6.0</b>
<br>
Professional SEO analysis and client reporting platform

</div>
""",
    unsafe_allow_html=True,
)
