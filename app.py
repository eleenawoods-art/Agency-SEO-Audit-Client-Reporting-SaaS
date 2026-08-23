import streamlit as st
import pandas as pd
from collections import defaultdict

from modules.crawler import crawl_website, normalize_url
from modules.seo_audit import audit_page, audit_links, robots_and_sitemap
from modules.scoring import (
    calculate_score,
    score_label,
    calculate_category_scores,
)
from reports.pdf_report import build_pdf_report


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Agency SEO Auditor",
    page_icon="🔎",
    layout="wide",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 2px;
    }

    .subtitle {
        font-size: 17px;
        color: #667085;
        margin-bottom: 25px;
    }

    .hero-card {
        padding: 28px;
        border-radius: 20px;
        background: linear-gradient(
            135deg,
            #f8fafc 0%,
            #eef2ff 100%
        );
        border: 1px solid #e2e8f0;
    }

    .score-title {
        text-align: center;
        font-size: 13px;
        font-weight: 700;
        color: #667085;
        letter-spacing: 1px;
    }

    .score-number {
        text-align: center;
        font-size: 64px;
        font-weight: 850;
        line-height: 1.1;
        margin-top: 8px;
    }

    .score-status {
        text-align: center;
        font-size: 18px;
        font-weight: 750;
        margin-top: 8px;
    }

    .metric-card {
        padding: 18px;
        border-radius: 15px;
        background: white;
        border: 1px solid #e4e7ec;
        text-align: center;
        min-height: 105px;
    }

    .metric-number {
        font-size: 29px;
        font-weight: 800;
    }

    .metric-label {
        font-size: 13px;
        color: #667085;
        margin-top: 4px;
    }

    .category-card {
        padding: 18px;
        border-radius: 15px;
        background: white;
        border: 1px solid #e4e7ec;
    }

    .category-name {
        font-size: 15px;
        font-weight: 750;
    }

    .category-number {
        font-size: 27px;
        font-weight: 800;
        margin-top: 5px;
    }

    .issue-card {
        padding: 17px;
        border-radius: 14px;
        background: white;
        border: 1px solid #e4e7ec;
        margin-bottom: 10px;
    }

    .critical-card {
        border-left: 5px solid #dc2626;
    }

    .warning-card {
        border-left: 5px solid #f59e0b;
    }

    .issue-title {
        font-weight: 750;
        font-size: 15px;
    }

    .issue-meta {
        color: #667085;
        font-size: 12px;
        margin-top: 4px;
    }

    .issue-fix {
        font-size: 13px;
        margin-top: 9px;
    }

    .summary-box {
        padding: 20px;
        border-radius: 15px;
        background: #f8fafc;
        border-left: 5px solid #4f46e5;
        line-height: 1.7;
        margin-bottom: 18px;
    }

    .action-box {
        padding: 18px;
        border-radius: 14px;
        background: #f8fafc;
        border: 1px solid #e4e7ec;
        margin-bottom: 9px;
    }

    .action-number {
        font-weight: 800;
        margin-right: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================

def normalize_category(category):
    mapping = {
        "Images": "Image SEO",
        "Image SEO": "Image SEO",
        "Technical": "Technical SEO",
        "Technical SEO": "Technical SEO",
        "On-Page": "On-Page SEO",
        "On-Page SEO": "On-Page SEO",
        "Content": "Content",
        "Social": "Social SEO",
        "Social SEO": "Social SEO",
        "Security": "Security",
        "Mobile": "Mobile SEO",
        "Mobile SEO": "Mobile SEO",
    }

    return mapping.get(
        category,
        category or "Other"
    )


def aggregate_issues(results):
    """
    Groups identical findings together.

    Example:
    '9 images missing alt text'
    '1 image missing alt text'
    '24 images missing alt text'

    becomes one client-friendly finding.
    """

    groups = defaultdict(
        lambda: {
            "category": "",
            "severity": "",
            "issue": "",
            "recommendation": "",
            "count": 0,
            "pages": set(),
        }
    )

    for result in results:

        category = normalize_category(
            result.get("category")
        )

        severity = result.get(
            "severity",
            "Warning"
        )

        issue = result.get(
            "issue",
            "SEO issue"
        )

        recommendation = result.get(
            "recommendation",
            "Review and fix this issue."
        )

        # Remove changing numeric prefixes so similar
        # findings can be grouped.
        import re

        normalized_issue = re.sub(
            r"^\d+\s+",
            "",
            issue
        )

        normalized_issue = re.sub(
            r"\b\d+\s+image\(s\)",
            "IMAGE_COUNT image(s)",
            normalized_issue,
            flags=re.IGNORECASE
        )

        normalized_issue = re.sub(
            r"\b\d+\s+recommended security header\(s\)",
            "SECURITY_HEADERS recommended security header(s)",
            normalized_issue,
            flags=re.IGNORECASE
        )

        key = (
            category,
            severity,
            normalized_issue.lower()
        )

        group = groups[key]

        group["category"] = category
        group["severity"] = severity
        group["issue"] = normalized_issue
        group["recommendation"] = recommendation

        # Every individual audit result counts.
        group["count"] += 1

        # Try common page fields.
        page = (
            result.get("url")
            or result.get("page")
            or result.get("Page")
            or result.get("URL")
        )

        if page:
            group["pages"].add(page)

    aggregated = []

    for group in groups.values():

        pages = sorted(
            group["pages"]
        )

        issue_text = group["issue"]

        # Restore useful wording for image findings.
        if "IMAGE_COUNT" in issue_text:

            issue_text = (
                "Images missing alt text"
            )

        if "SECURITY_HEADERS" in issue_text:

            issue_text = (
                "Recommended security headers missing"
            )

        aggregated.append(
            {
                "category": group["category"],
                "severity": group["severity"],
                "issue": issue_text,
                "recommendation": group["recommendation"],
                "occurrences": group["count"],
                "affected_pages": len(pages),
                "pages": pages,
            }
        )

    # Critical first, then warnings, then passed.
    priority = {
        "Critical": 0,
        "Warning": 1,
        "Passed": 2,
    }

    aggregated.sort(
        key=lambda item: (
            priority.get(
                item["severity"],
                3
            ),
            -item["occurrences"],
        )
    )

    return aggregated


def get_action_plan(aggregated):
    actions = []

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

    for item in critical[:3]:

        actions.append(
            (
                "Critical",
                item["issue"],
                item["recommendation"]
            )
        )

    for item in warnings[:5]:

        actions.append(
            (
                "Warning",
                item["issue"],
                item["recommendation"]
            )
        )

    return actions[:6]


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🔎 Agency SEO Auditor</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Professional SEO auditing and client reporting platform'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("🏢 Agency Profile")

    agency_name = st.text_input(
        "Agency Name",
        value="Your SEO Agency"
    )

    agency_website = st.text_input(
        "Agency Website",
        placeholder="https://youragency.com"
    )

    agency_email = st.text_input(
        "Agency Email",
        placeholder="hello@youragency.com"
    )

    logo_file = st.file_uploader(
        "Agency Logo",
        type=["png", "jpg", "jpeg"]
    )

    st.divider()

    st.header("⚙️ Audit Settings")

    max_pages = st.slider(
        "Pages to crawl",
        1,
        30,
        10
    )

    check_links = st.checkbox(
        "Check broken links",
        value=True
    )

    st.divider()

    st.caption(
        "Agency SEO Auditor v5.0"
    )


# =========================================================
# CLIENT INFORMATION
# =========================================================

st.subheader(
    "👤 Client Information"
)

client_col1, client_col2 = st.columns(2)

with client_col1:

    client_name = st.text_input(
        "Client / Company Name",
        placeholder="Example: ABC Digital"
    )

with client_col2:

    client_website = st.text_input(
        "Client Website",
        placeholder="https://example.com"
    )


# =========================================================
# AUDIT URL
# =========================================================

audit_url = st.text_input(
    "🌐 Website URL to Audit",
    placeholder="https://example.com"
)

audit_button = st.button(
    "🚀 Start SEO Audit",
    type="primary",
    use_container_width=True
)


# =========================================================
# RUN AUDIT
# =========================================================

if audit_button:

    if not audit_url.strip():

        st.error(
            "Please enter a website URL."
        )

        st.stop()

    audit_url = normalize_url(
        audit_url
    )

    if not client_website.strip():

        client_website = audit_url

    with st.spinner(
        "Crawling website and analyzing SEO..."
    ):

        pages = crawl_website(
            audit_url,
            max_pages=max_pages
        )

    if not pages:

        st.error(
            "Unable to crawl this website. "
            "Please check the URL and try again."
        )

        st.stop()

    all_results = []
    page_summaries = []
    broken_links = []

    progress = st.progress(0)

    for index, page in enumerate(pages):

        results = audit_page(
            page
        )

        all_results.extend(
            results
        )

        issue_count = sum(
            1
            for result in results
            if result.get("severity")
            in ["Critical", "Warning"]
        )

        page_summaries.append(
            {
                "URL": page["url"],
                "Status": page["status"],
                "Title": page["title"],
                "Issues": issue_count
            }
        )

        if check_links:

            try:

                broken = audit_links(
                    page
                )

                for item in broken:

                    item["Page"] = page["url"]

                    broken_links.append(
                        item
                    )

            except Exception:

                pass

        progress.progress(
            (index + 1) / len(pages)
        )

    technical_files = robots_and_sitemap(
        audit_url
    )

    score = calculate_score(
        all_results
    )

    label = score_label(
        score
    )

    category_scores = calculate_category_scores(
        all_results
    )

    aggregated = aggregate_issues(
        all_results
    )

    action_plan = get_action_plan(
        aggregated
    )

    st.session_state["results"] = all_results
    st.session_state["aggregated"] = aggregated
    st.session_state["action_plan"] = action_plan
    st.session_state["pages"] = page_summaries
    st.session_state["broken_links"] = broken_links
    st.session_state["score"] = score
    st.session_state["label"] = label
    st.session_state["category_scores"] = category_scores
    st.session_state["technical_files"] = technical_files
    st.session_state["audit_url"] = audit_url


# =========================================================
# DISPLAY RESULTS
# =========================================================

if "results" in st.session_state:

    results = st.session_state["results"]

    aggregated = st.session_state[
        "aggregated"
    ]

    action_plan = st.session_state[
        "action_plan"
    ]

    pages = st.session_state["pages"]

    broken_links = st.session_state[
        "broken_links"
    ]

    score = st.session_state["score"]

    label = st.session_state["label"]

    category_scores = st.session_state[
        "category_scores"
    ]

    technical_files = st.session_state[
        "technical_files"
    ]

    audit_url = st.session_state[
        "audit_url"
    ]


    # =====================================================
    # COUNTS
    # =====================================================

    critical = sum(
        1
        for result in results
        if result.get("severity") == "Critical"
    )

    warnings = sum(
        1
        for result in results
        if result.get("severity") == "Warning"
    )

    passed = sum(
        1
        for result in results
        if result.get("severity") == "Passed"
    )

    total_checks = len(results)


    # =====================================================
    # DASHBOARD
    # =====================================================

    st.divider()

    st.subheader(
        "📊 SEO Performance Dashboard"
    )

    st.caption(
        "Client-ready website health overview "
        "and prioritized SEO recommendations."
    )


    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    summary = (
        f"The website currently has an SEO score of "
        f"<b>{score}/100</b>, classified as "
        f"<b>{label}</b>. "
        f"The audit detected <b>{critical}</b> critical "
        f"issues, <b>{warnings}</b> warnings, and "
        f"<b>{passed}</b> passed checks."
    )

    st.markdown(
        f"""
        <div class="summary-box">
            <b>Executive Summary</b><br>
            {summary}
        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # SCORE + METRICS
    # =====================================================

    score_col, metric_col = st.columns(
        [1, 2]
    )

    with score_col:

        st.markdown(
            f"""
            <div class="hero-card">

                <div class="score-title">
                    OVERALL SEO SCORE
                </div>

                <div class="score-number">
                    {score}
                </div>

                <div class="score-title">
                    OUT OF 100
                </div>

                <div class="score-status">
                    {label}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        st.progress(
            score / 100
        )

    with metric_col:

        cols = st.columns(3)

        metrics = [
            ("🔴", critical, "Critical Issues"),
            ("🟠", warnings, "Warnings"),
            ("🟢", passed, "Passed Checks"),
        ]

        for col, metric in zip(
            cols,
            metrics
        ):

            icon, value, title = metric

            with col:

                st.markdown(
                    f"""
                    <div class="metric-card">

                        <div class="metric-number">
                            {icon} {value}
                        </div>

                        <div class="metric-label">
                            {title}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.info(
            f"Audited website: {audit_url}"
        )


    # =====================================================
    # CATEGORY SCORES
    # =====================================================

    st.subheader(
        "📈 SEO Category Performance"
    )

    category_order = [
        "Technical SEO",
        "On-Page SEO",
        "Content",
        "Image SEO",
        "Social SEO",
        "Security",
        "Mobile SEO",
    ]

    normalized_scores = {}

    for category, value in category_scores.items():

        normalized_scores[
            normalize_category(category)
        ] = value

    available_categories = [
        category
        for category in category_order
        if category in normalized_scores
    ]

    for start in range(
        0,
        len(available_categories),
        3
    ):

        current = available_categories[
            start:start + 3
        ]

        cols = st.columns(
            len(current)
        )

        for col, category in zip(
            cols,
            current
        ):

            value = normalized_scores[
                category
            ]

            if value >= 90:
                status = "Excellent"
            elif value >= 75:
                status = "Good"
            elif value >= 50:
                status = "Needs Improvement"
            else:
                status = "Poor"

            with col:

                st.markdown(
                    f"""
                    <div class="category-card">

                        <div class="category-name">
                            {category}
                        </div>

                        <div class="category-number">
                            {value}/100
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.progress(
                    value / 100
                )

                st.caption(
                    f"Status: {status}"
                )


    # =====================================================
    # PRIORITY FINDINGS
    # =====================================================

    st.subheader(
        "🚨 Prioritized SEO Findings"
    )

    critical_findings = [
        item
        for item in aggregated
        if item["severity"] == "Critical"
    ]

    warning_findings = [
        item
        for item in aggregated
        if item["severity"] == "Warning"
    ]

    if critical_findings:

        st.markdown(
            "### 🔴 Critical Issues"
        )

        for item in critical_findings:

            page_text = (
                f'{item["affected_pages"]} affected page'
                + (
                    "s"
                    if item["affected_pages"] != 1
                    else ""
                )
            )

            st.markdown(
                f"""
                <div class="issue-card critical-card">

                    <div class="issue-title">
                        🔴 {item["issue"]}
                    </div>

                    <div class="issue-meta">
                        {item["category"]} ·
                        {item["occurrences"]} occurrence(s) ·
                        {page_text}
                    </div>

                    <div class="issue-fix">
                        <b>Recommended Fix:</b>
                        {item["recommendation"]}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.success(
            "No critical issues detected."
        )


    if warning_findings:

        st.markdown(
            "### 🟠 Warnings"
        )

        for item in warning_findings[:10]:

            page_text = (
                f'{item["affected_pages"]} affected page'
                + (
                    "s"
                    if item["affected_pages"] != 1
                    else ""
                )
            )

            st.markdown(
                f"""
                <div class="issue-card warning-card">

                    <div class="issue-title">
                        🟠 {item["issue"]}
                    </div>

                    <div class="issue-meta">
                        {item["category"]} ·
                        {item["occurrences"]} occurrence(s) ·
                        {page_text}
                    </div>

                    <div class="issue-fix">
                        <b>Recommended Fix:</b>
                        {item["recommendation"]}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


    # =====================================================
    # ACTION PLAN
    # =====================================================

    st.subheader(
        "🛠️ Recommended Action Plan"
    )

    if action_plan:

        for index, action in enumerate(
            action_plan,
            start=1
        ):

            severity, issue, recommendation = action

            st.markdown(
                f"""
                <div class="action-box">

                    <span class="action-number">
                        {index}.
                    </span>

                    <b>{issue}</b>

                    <br>

                    <small>
                        {recommendation}
                    </small>

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.success(
            "No immediate action items. "
            "The website is performing well."
        )


    # =====================================================
    # PDF REPORT
    # =====================================================

    st.divider()

    st.subheader(
        "📄 Client Report"
    )

    st.caption(
        "Generate a professional white-label PDF report "
        "for your client."
    )

    logo_bytes = None

    if logo_file is not None:

        logo_bytes = logo_file.getvalue()

    try:

        pdf_bytes = build_pdf_report(
            agency_name=agency_name,
            agency_website=agency_website,
            agency_email=agency_email,
            client_name=client_name or "Client",
            client_website=client_website or audit_url,
            score=score,
            score_label=label,
            results=results,
            pages=pages,
            broken_links=broken_links,
            technical_files=technical_files,
            logo_bytes=logo_bytes
        )

        st.download_button(
            "📥 Download Professional PDF Report",
            data=pdf_bytes,
            file_name=(
                "SEO_Audit_Report_"
                + (
                    client_name or "Client"
                ).replace(
                    " ",
                    "_"
                )
                + ".pdf"
            ),
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as error:

        st.error(
            f"PDF generation error: {error}"
        )


    # =====================================================
    # DETAILED TABS
    # =====================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Audit Results",
            "🌐 Pages",
            "🔗 Broken Links",
            "⚙️ Technical",
        ]
    )


    # =====================================================
    # AUDIT RESULTS
    # =====================================================

    with tab1:

        df = pd.DataFrame(
            results
        )

        if not df.empty:

            severity_filter = st.multiselect(
                "Filter by severity",
                [
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

            filtered = df[
                df["severity"].isin(
                    severity_filter
                )
            ]

            st.dataframe(
                filtered,
                use_container_width=True,
                hide_index=True,
            )

            csv = filtered.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download Audit CSV",
                csv,
                "seo_audit_report.csv",
                "text/csv",
            )


    # =====================================================
    # PAGES
    # =====================================================

    with tab2:

        pages_df = pd.DataFrame(
            pages
        )

        st.dataframe(
            pages_df,
            use_container_width=True,
            hide_index=True,
        )


    # =====================================================
    # BROKEN LINKS
    # =====================================================

    with tab3:

        if broken_links:

            broken_df = pd.DataFrame(
                broken_links
            )

            st.error(
                f"{len(broken_links)} broken link(s) detected."
            )

            st.dataframe(
                broken_df,
                use_container_width=True,
                hide_index=True,
            )

            csv = broken_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download Broken Links CSV",
                csv,
                "broken_links.csv",
                "text/csv",
            )

        else:

            st.success(
                "No broken links detected in "
                "the checked pages."
            )


    # =====================================================
    # TECHNICAL
    # =====================================================

    with tab4:

        robots = technical_files["robots"]
        sitemap = technical_files["sitemap"]

        col1, col2 = st.columns(2)

        with col1:

            st.subheader(
                "🤖 robots.txt"
            )

            if robots["working"]:

                st.success(
                    f"Found — HTTP {robots['status']}"
                )

            else:

                st.warning(
                    "robots.txt not found or unavailable."
                )

        with col2:

            st.subheader(
                "🗺️ sitemap.xml"
            )

            if sitemap["working"]:

                st.success(
                    f"Found — HTTP {sitemap['status']}"
                )

            else:

                st.warning(
                    "sitemap.xml not found or unavailable."
                )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Agency SEO Auditor v5.0 | "
    "Professional SEO analysis and client reporting platform."
)
