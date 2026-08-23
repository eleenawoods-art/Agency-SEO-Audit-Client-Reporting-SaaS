import streamlit as st
import pandas as pd

from modules.crawler import (
    crawl_website,
    normalize_url
)

from modules.seo_audit import (
    audit_page,
    audit_links,
    robots_and_sitemap
)

from modules.scoring import (
    calculate_score,
    score_label,
    calculate_category_scores
)

from reports.pdf_report import build_pdf_report


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Agency SEO Auditor",
    page_icon="🔎",
    layout="wide"
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
        margin-bottom: 3px;
    }

    .subtitle {
        font-size: 17px;
        color: #777;
        margin-bottom: 25px;
    }

    .score-card {
        padding: 24px;
        border-radius: 16px;
        background: #f7f8fa;
        border: 1px solid #e4e7ec;
        text-align: center;
        margin-bottom: 20px;
    }

    .score-number {
        font-size: 58px;
        font-weight: 800;
        line-height: 1;
        margin: 8px 0;
    }

    .score-label {
        font-size: 17px;
        font-weight: 600;
    }

    .dashboard-card {
        padding: 18px;
        border-radius: 14px;
        background: #ffffff;
        border: 1px solid #e4e7ec;
        margin-bottom: 10px;
    }

    .category-title {
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 7px;
    }

    .category-score {
        font-size: 26px;
        font-weight: 800;
    }

    .priority-box {
        padding: 15px;
        border-radius: 12px;
        background: #fff7ed;
        border: 1px solid #fed7aa;
        margin-bottom: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


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
        min_value=1,
        max_value=30,
        value=10
    )

    check_links = st.checkbox(
        "Check broken links",
        value=True
    )

    st.divider()

    st.caption(
        "Agency SEO Auditor v3.0"
    )


# =========================================================
# CLIENT INFORMATION
# =========================================================

st.subheader("👤 Client Information")

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
# URL
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

        page_summaries.append(
            {
                "URL": page["url"],
                "Status": page["status"],
                "Title": page["title"],
                "Issues": sum(
                    1
                    for result in results
                    if result["severity"]
                    in [
                        "Critical",
                        "Warning"
                    ]
                )
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

    # Save results
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
    # OVERALL DASHBOARD
    # =====================================================

    st.divider()

    st.subheader(
        "📊 SEO Performance Dashboard"
    )

    # Top metrics

    critical = sum(
        1
        for result in results
        if result["severity"] == "Critical"
    )

    warnings = sum(
        1
        for result in results
        if result["severity"] == "Warning"
    )

    passed = sum(
        1
        for result in results
        if result["severity"] == "Passed"
    )

    total_checks = len(results)


    # =====================================================
    # SCORE CARD
    # =====================================================

    score_col1, score_col2 = st.columns(
        [1, 2]
    )

    with score_col1:

        st.markdown(
            f"""
            <div class="score-card">

                <div>OVERALL SEO SCORE</div>

                <div class="score-number">
                    {score}/100
                </div>

                <div class="score-label">
                    {label}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        st.progress(
            score / 100
        )


    with score_col2:

        m1, m2, m3, m4 = st.columns(4)

        with m1:

            st.metric(
                "🔴 Critical",
                critical
            )

        with m2:

            st.metric(
                "🟠 Warnings",
                warnings
            )

        with m3:

            st.metric(
                "🟢 Passed",
                passed
            )

        with m4:

            st.metric(
                "Checks",
                total_checks
            )


        st.info(
            f"Audit completed for **{audit_url}**"
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
        "Mobile SEO"
    ]

    available_categories = [
        category
        for category in category_order
        if category in category_scores
    ]

    # Display 4 per row
    for start in range(
        0,
        len(available_categories),
        4
    ):

        row_categories = available_categories[
            start:start + 4
        ]

        cols = st.columns(
            len(row_categories)
        )

        for col, category in zip(
            cols,
            row_categories
        ):

            category_score = category_scores[
                category
            ]

            with col:

                st.markdown(
                    f"""
                    <div class="dashboard-card">

                        <div class="category-title">
                            {category}
                        </div>

                        <div class="category-score">
                            {category_score}/100
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.progress(
                    category_score / 100
                )


    # =====================================================
    # PRIORITY ISSUES
    # =====================================================

    st.subheader(
        "🚨 Top Priority Issues"
    )

    priority_issues = [
        result
        for result in results
        if result["severity"]
        in [
            "Critical",
            "Warning"
        ]
    ]

    priority_issues = priority_issues[
        :8
    ]

    if priority_issues:

        for issue in priority_issues:

            severity = issue[
                "severity"
            ]

            icon = (
                "🔴"
                if severity == "Critical"
                else "🟠"
            )

            st.markdown(
                f"""
                <div class="priority-box">

                    <b>
                        {icon} {issue["issue"]}
                    </b>

                    <br>

                    <small>
                        {issue["category"]}
                    </small>

                    <br><br>

                    <b>Recommended Fix:</b>
                    {issue["recommendation"]}

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.success(
            "🎉 No critical or warning issues detected."
        )


    # =====================================================
    # CLIENT PDF REPORT
    # =====================================================

    st.divider()

    st.subheader(
        "📄 Client Report"
    )

    st.write(
        "Generate a professional white-label "
        "PDF report for your client."
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
            "⚙️ Technical"
        ]
    )


    # =====================================================
    # TAB 1
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
                    "Passed"
                ],
                default=[
                    "Critical",
                    "Warning",
                    "Passed"
                ]
            )

            filtered = df[
                df["severity"].isin(
                    severity_filter
                )
            ]

            st.dataframe(
                filtered,
                use_container_width=True,
                hide_index=True
            )

            csv = filtered.to_csv(
                index=False
            ).encode(
                "utf-8"
            )

            st.download_button(
                "⬇️ Download Audit CSV",
                csv,
                "seo_audit_report.csv",
                "text/csv"
            )


    # =====================================================
    # TAB 2
    # =====================================================

    with tab2:

        pages_df = pd.DataFrame(
            pages
        )

        st.dataframe(
            pages_df,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # TAB 3
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
                hide_index=True
            )

            csv = broken_df.to_csv(
                index=False
            ).encode(
                "utf-8"
            )

            st.download_button(
                "⬇️ Download Broken Links CSV",
                csv,
                "broken_links.csv",
                "text/csv"
            )

        else:

            st.success(
                "No broken links detected "
                "in the checked pages."
            )


    # =====================================================
    # TAB 4
    # =====================================================

    with tab4:

        robots = technical_files[
            "robots"
        ]

        sitemap = technical_files[
            "sitemap"
        ]

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
                    "robots.txt not found "
                    "or unavailable."
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
                    "sitemap.xml not found "
                    "or unavailable."
                )


    # =====================================================
    # FOOTER
    # =====================================================

    st.divider()

    st.caption(
        "Agency SEO Auditor v3.0 | "
        "Professional SEO analysis and client reporting platform."
    )
