import streamlit as st
import pandas as pd

from modules.crawler import crawl_website, normalize_url
from modules.seo_audit import audit_page, audit_links, robots_and_sitemap
from modules.scoring import calculate_score, score_label
from reports.pdf_report import build_pdf_report


st.set_page_config(
    page_title="Agency SEO Auditor",
    page_icon="🔎",
    layout="wide"
)


st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 5px;
}

.subtitle {
    font-size: 18px;
    color: #777;
    margin-bottom: 25px;
}

.report-card {
    padding: 20px;
    border-radius: 15px;
    background: #f5f7fa;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


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
# SIDEBAR - AGENCY BRANDING
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

    st.caption("Agency SEO Auditor v2.0")


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
# AUDIT
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

        results = audit_page(page)

        all_results.extend(results)

        page_summaries.append(
            {
                "URL": page["url"],
                "Status": page["status"],
                "Title": page["title"],
                "Issues": sum(
                    1
                    for r in results
                    if r["severity"]
                    in ["Critical", "Warning"]
                )
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

    st.session_state["results"] = all_results
    st.session_state["pages"] = page_summaries
    st.session_state["broken_links"] = broken_links
    st.session_state["score"] = score
    st.session_state["label"] = label
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

    technical_files = st.session_state[
        "technical_files"
    ]

    audit_url = st.session_state[
        "audit_url"
    ]

    st.divider()

    st.subheader(
        "📊 SEO Performance Overview"
    )

    critical = sum(
        1
        for r in results
        if r["severity"] == "Critical"
    )

    warnings = sum(
        1
        for r in results
        if r["severity"] == "Warning"
    )

    passed = sum(
        1
        for r in results
        if r["severity"] == "Passed"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "SEO Score",
            f"{score}/100"
        )

    with col2:
        st.metric(
            "Critical Issues",
            critical
        )

    with col3:
        st.metric(
            "Warnings",
            warnings
        )

    with col4:
        st.metric(
            "Passed Checks",
            passed
        )

    st.info(
        f"Overall assessment: **{label}**"
    )


    # =====================================================
    # PDF REPORT
    # =====================================================

    st.divider()

    st.subheader(
        "📄 Client Report"
    )

    st.write(
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
            logo_bytes=logo_bytes,
        )

        st.download_button(
            "📥 Download Professional PDF Report",
            data=pdf_bytes,
            file_name=(
                f"SEO_Audit_Report_"
                f"{(client_name or 'Client').replace(' ', '_')}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:

        st.error(
            f"PDF generation error: {str(e)}"
        )


    # =====================================================
    # TABS
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
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download Audit CSV",
                csv,
                "seo_audit_report.csv",
                "text/csv"
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
            hide_index=True
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
                hide_index=True
            )

            csv = broken_df.to_csv(
                index=False
            ).encode("utf-8")

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
    # TECHNICAL
    # =====================================================

    with tab4:

        robots = technical_files["robots"]

        sitemap = technical_files["sitemap"]

        c1, c2 = st.columns(2)

        with c1:

            st.subheader(
                "robots.txt"
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

        with c2:

            st.subheader(
                "sitemap.xml"
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


    st.divider()

    st.caption(
        "Agency SEO Auditor v2.0 | "
        "Automated SEO analysis and client reporting."
    )
