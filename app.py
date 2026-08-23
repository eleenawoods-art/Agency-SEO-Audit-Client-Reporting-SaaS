import streamlit as st
import pandas as pd

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
# CUSTOM CSS
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
        color: #777;
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
        margin-bottom: 20px;
    }

    .score-number {
        font-size: 64px;
        font-weight: 850;
        line-height: 1;
        text-align: center;
    }

    .score-title {
        text-align: center;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1px;
        color: #667085;
    }

    .score-status {
        text-align: center;
        font-size: 18px;
        font-weight: 700;
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
        margin-bottom: 12px;
    }

    .category-name {
        font-size: 15px;
        font-weight: 750;
    }

    .category-number {
        font-size: 27px;
        font-weight: 800;
        margin-top: 4px;
    }

    .issue-card {
        padding: 16px 18px;
        border-radius: 13px;
        background: #fff;
        border: 1px solid #e4e7ec;
        margin-bottom: 9px;
    }

    .issue-title {
        font-weight: 750;
        font-size: 15px;
    }

    .issue-category {
        color: #667085;
        font-size: 12px;
        margin-top: 3px;
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

    .section-note {
        color: #667085;
        font-size: 14px;
        margin-bottom: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🔎 Agency SEO Auditor</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Professional SEO auditing and client reporting platform'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("🏢 Agency Profile")

    agency_name = st.text_input(
        "Agency Name",
        value="Your SEO Agency",
    )

    agency_website = st.text_input(
        "Agency Website",
        placeholder="https://youragency.com",
    )

    agency_email = st.text_input(
        "Agency Email",
        placeholder="hello@youragency.com",
    )

    logo_file = st.file_uploader(
        "Agency Logo",
        type=["png", "jpg", "jpeg"],
    )

    st.divider()

    st.header("⚙️ Audit Settings")

    max_pages = st.slider(
        "Pages to crawl",
        min_value=1,
        max_value=30,
        value=10,
    )

    check_links = st.checkbox(
        "Check broken links",
        value=True,
    )

    st.divider()

    st.caption("Agency SEO Auditor v4.0")


# =========================================================
# CLIENT INFORMATION
# =========================================================

st.subheader("👤 Client Information")

client_col1, client_col2 = st.columns(2)

with client_col1:

    client_name = st.text_input(
        "Client / Company Name",
        placeholder="Example: ABC Digital",
    )

with client_col2:

    client_website = st.text_input(
        "Client Website",
        placeholder="https://example.com",
    )


# =========================================================
# WEBSITE URL
# =========================================================

audit_url = st.text_input(
    "🌐 Website URL to Audit",
    placeholder="https://example.com",
)


audit_button = st.button(
    "🚀 Start SEO Audit",
    type="primary",
    use_container_width=True,
)


# =========================================================
# RUN AUDIT
# =========================================================

if audit_button:

    if not audit_url.strip():

        st.error("Please enter a website URL.")
        st.stop()

    audit_url = normalize_url(audit_url)

    if not client_website.strip():
        client_website = audit_url

    with st.spinner(
        "Crawling website and analyzing SEO..."
    ):

        pages = crawl_website(
            audit_url,
            max_pages=max_pages,
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

        results = audit_page(page)

        all_results.extend(results)

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
                "Issues": issue_count,
            }
        )

        if check_links:

            try:

                broken = audit_links(page)

                for item in broken:

                    item["Page"] = page["url"]
                    broken_links.append(item)

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

    label = score_label(score)

    category_scores = calculate_category_scores(
        all_results
    )

    st.session_state["results"] = all_results
    st.session_state["pages"] = page_summaries
    st.session_state["broken_links"] = broken_links
    st.session_state["score"] = score
    st.session_state["label"] = label
    st.session_state["category_scores"] = category_scores
    st.session_state["technical_files"] = technical_files
    st.session_state["audit_url"] = audit_url


# =========================================================
# RESULTS
# =========================================================

if "results" in st.session_state:

    results = st.session_state["results"]
    pages = st.session_state["pages"]
    broken_links = st.session_state["broken_links"]
    score = st.session_state["score"]
    label = st.session_state["label"]
    category_scores = st.session_state["category_scores"]
    technical_files = st.session_state["technical_files"]
    audit_url = st.session_state["audit_url"]


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

    st.markdown(
        '<div class="section-note">'
        'A client-ready overview of the website health and '
        'highest-priority SEO opportunities.'
        '</div>',
        unsafe_allow_html=True,
    )


    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    critical_text = (
        "no critical issues"
        if critical == 0
        else f"{critical} critical issue"
        + ("s" if critical != 1 else "")
    )

    warning_text = (
        "no warnings"
        if warnings == 0
        else f"{warnings} warning"
        + ("s" if warnings != 1 else "")
    )

    summary = (
        f"The website currently has an SEO score of "
        f"<b>{score}/100</b>, classified as "
        f"<b>{label}</b>. The audit detected "
        f"<b>{critical_text}</b> and "
        f"<b>{warning_text}</b>, while "
        f"<b>{passed}</b> checks passed successfully."
    )

    st.markdown(
        f"""
        <div class="summary-box">
            <b>Executive Summary</b><br>
            {summary}
        </div>
        """,
        unsafe_allow_html=True,
    )


    # =====================================================
    # SCORE + METRICS
    # =====================================================

    hero_col, metrics_col = st.columns(
        [1, 2]
    )

    with hero_col:

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
            unsafe_allow_html=True,
        )

        st.progress(
            max(0, min(score, 100)) / 100
        )


    with metrics_col:

        row1 = st.columns(3)

        with row1[0]:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-number">
                        🔴 {critical}
                    </div>

                    <div class="metric-label">
                        Critical Issues
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        with row1[1]:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-number">
                        🟠 {warnings}
                    </div>

                    <div class="metric-label">
                        Warnings
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        with row1[2]:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-number">
                        🟢 {passed}
                    </div>

                    <div class="metric-label">
                        Passed Checks
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        st.info(
            f"Audited website: {audit_url}"
        )


    # =====================================================
    # CATEGORY PERFORMANCE
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

    available_categories = [
        category
        for category in category_order
        if category in category_scores
    ]

    for start in range(
        0,
        len(available_categories),
        3,
    ):

        current_categories = available_categories[
            start:start + 3
        ]

        cols = st.columns(
            len(current_categories)
        )

        for col, category in zip(
            cols,
            current_categories,
        ):

            category_score = category_scores[
                category
            ]

            with col:

                st.markdown(
                    f"""
                    <div class="category-card">

                        <div class="category-name">
                            {category}
                        </div>

                        <div class="category-number">
                            {category_score}/100
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.progress(
                    category_score / 100
                )

                if category_score >= 90:
                    status = "Excellent"
                elif category_score >= 75:
                    status = "Good"
                elif category_score >= 50:
                    status = "Needs Improvement"
                else:
                    status = "Poor"

                st.caption(
                    f"Status: {status}"
                )


    # =====================================================
    # TOP PRIORITY ISSUES
    # =====================================================

    st.subheader(
        "🚨 Top Priority Issues"
    )

    priority_issues = [
        result
        for result in results
        if result.get("severity")
        in ["Critical", "Warning"]
    ]

    priority_issues = priority_issues[:8]

    if priority_issues:

        for issue in priority_issues:

            severity = issue.get(
                "severity",
                "Warning",
            )

            if severity == "Critical":
                icon = "🔴"
            else:
                icon = "🟠"

            issue_title = issue.get(
                "issue",
                "SEO issue",
            )

            category = issue.get(
                "category",
                "SEO",
            )

            recommendation = issue.get(
                "recommendation",
                "Review this issue.",
            )

            st.markdown(
                f"""
                <div class="issue-card">

                    <div class="issue-title">
                        {icon} {issue_title}
                    </div>

                    <div class="issue-category">
                        {category}
                    </div>

                    <div class="issue-fix">
                        <b>Recommended Fix:</b>
                        {recommendation}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    else:

        st.success(
            "🎉 Excellent! No critical or warning issues "
            "were detected."
        )


    # =====================================================
    # PDF REPORT
    # =====================================================

    st.divider()

    st.subheader(
        "📄 Client Report"
    )

    st.markdown(
        '<div class="section-note">'
        'Generate a professional white-label PDF report '
        'for your client.'
        '</div>',
        unsafe_allow_html=True,
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
            logo_bytes=logo_bytes,
        )

        st.download_button(
            "📥 Download Professional PDF Report",
            data=pdf_bytes,
            file_name=(
                "SEO_Audit_Report_"
                + (client_name or "Client").replace(
                    " ",
                    "_",
                )
                + ".pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

    except Exception as error:

        st.error(
            f"PDF generation error: {error}"
        )


    # =====================================================
    # DETAILED DATA
    # =====================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Audit Results",
            "🌐 Pages",
            "🔗 Broken Links",
            "⚙️ Technical",
        ]
    )


    with tab1:

        df = pd.DataFrame(results)

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


    with tab2:

        pages_df = pd.DataFrame(pages)

        st.dataframe(
            pages_df,
            use_container_width=True,
            hide_index=True,
        )


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
                "No broken links detected in the "
                "checked pages."
            )


    with tab4:

        robots = technical_files["robots"]
        sitemap = technical_files["sitemap"]

        technical_col1, technical_col2 = st.columns(2)

        with technical_col1:

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

        with technical_col2:

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


    # =====================================================
    # FOOTER
    # =====================================================

    st.divider()

    st.caption(
        "Agency SEO Auditor v4.0 | "
        "Professional SEO analysis and client reporting platform."
    )
