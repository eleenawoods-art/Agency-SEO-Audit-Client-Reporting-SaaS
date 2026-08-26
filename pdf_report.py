from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


def build_pdf_report(report_data=None, agency_name=None, agency_website=None, agency_email=None, client_name=None, client_website=None, score=0, score_label="", results=None, pages=None, broken_links=None, technical_files=None, logo_bytes=None):
    """Build a PDF report. Accepts either the v6 report_data dict or legacy keyword arguments."""
    if isinstance(report_data, dict):
        data = report_data
        agency_name = data.get("agency_name", agency_name)
        agency_website = data.get("agency_website", agency_website)
        agency_email = data.get("agency_email", agency_email)
        client_name = data.get("client_name", client_name)
        client_website = data.get("client_website") or data.get("audit_url") or client_website
        score = data.get("score", score)
        score_label = data.get("score_label", score_label)
        results = data.get("results", results)
        pages = data.get("pages", pages)
        broken_links = data.get("broken_links", broken_links)
        technical_files = data.get("technical", data.get("technical_files", technical_files))
    results = results or []
    pages = pages or []
    broken_links = broken_links or []
    technical_files = technical_files or {}

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"SEO Audit Report - {client_name}",
        author=agency_name,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=25,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=17,
        leading=22,
        spaceBefore=12,
        spaceAfter=10,
        textColor=colors.HexColor("#172033"),
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=5,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
    )

    story = []

    # ---------------------------------------------------------
    # COVER
    # ---------------------------------------------------------

    story.append(Spacer(1, 30 * mm))

    if logo_bytes:
        try:
            from reportlab.platypus import Image

            logo = Image(
                BytesIO(logo_bytes),
                width=38 * mm,
                height=20 * mm,
            )

            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 8 * mm))

        except Exception:
            pass

    story.append(
        Paragraph(
            "SEO AUDIT REPORT",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "Professional Website SEO Analysis",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 15 * mm))

    cover_data = [
        ["Prepared For", client_name or "Client"],
        ["Website", client_website or "N/A"],
        ["Prepared By", agency_name or "Agency"],
        ["Agency Website", agency_website or "N/A"],
        ["Report Date", datetime.now().strftime("%d %B %Y")],
    ]

    cover_table = Table(
        cover_data,
        colWidths=[45 * mm, 120 * mm],
    )

    cover_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#172033")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5D9E2")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(cover_table)
    story.append(PageBreak())

    # ---------------------------------------------------------
    # EXECUTIVE SUMMARY
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "1. Executive Summary",
            section_style,
        )
    )

    score_data = [
        [
            Paragraph("<b>SEO SCORE</b>", small_style),
            Paragraph("<b>CRITICAL</b>", small_style),
            Paragraph("<b>WARNINGS</b>", small_style),
            Paragraph("<b>PASSED</b>", small_style),
        ],
        [
            Paragraph(f"<b>{score}/100</b>", body_style),
            Paragraph(
                str(sum(1 for r in results if r["severity"] == "Critical")),
                body_style,
            ),
            Paragraph(
                str(sum(1 for r in results if r["severity"] == "Warning")),
                body_style,
            ),
            Paragraph(
                str(sum(1 for r in results if r["severity"] == "Passed")),
                body_style,
            ),
        ],
    ]

    score_table = Table(
        score_data,
        colWidths=[42 * mm, 42 * mm, 42 * mm, 42 * mm],
    )

    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F8")),
                ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#DDEBFF")),
                ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#FFE0E0")),
                ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#FFF0CF")),
                ("BACKGROUND", (3, 1), (3, 1), colors.HexColor("#DDF5E5")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5DD")),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    story.append(score_table)
    story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            f"<b>Overall Assessment:</b> {score_label}",
            body_style,
        )
    )

    story.append(
        Paragraph(
            "This report identifies technical, on-page, content, image, "
            "social and security-related SEO opportunities detected during "
            "the automated website audit.",
            body_style,
        )
    )

    # ---------------------------------------------------------
    # PRIORITY ISSUES
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "2. Priority Issues",
            section_style,
        )
    )

    priority_results = [
        r for r in results
        if r["severity"] in ("Critical", "Warning")
    ]

    if priority_results:

        issue_data = [
            [
                Paragraph("<b>Severity</b>", small_style),
                Paragraph("<b>Category</b>", small_style),
                Paragraph("<b>Issue</b>", small_style),
                Paragraph("<b>Recommendation</b>", small_style),
            ]
        ]

        for r in priority_results:

            issue_data.append(
                [
                    Paragraph(r["severity"], small_style),
                    Paragraph(r["category"], small_style),
                    Paragraph(r["issue"], small_style),
                    Paragraph(r["recommendation"], small_style),
                ]
            )

        issue_table = Table(
            issue_data,
            colWidths=[
                25 * mm,
                31 * mm,
                55 * mm,
                59 * mm,
            ],
            repeatRows=1,
        )

        issue_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(issue_table)

    else:

        story.append(
            Paragraph(
                "No critical or warning issues were detected.",
                body_style,
            )
        )

    # ---------------------------------------------------------
    # PAGE ANALYSIS
    # ---------------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "3. Page-by-Page Analysis",
            section_style,
        )
    )

    page_data = [
        [
            Paragraph("<b>URL</b>", small_style),
            Paragraph("<b>Status</b>", small_style),
            Paragraph("<b>Title</b>", small_style),
            Paragraph("<b>Issues</b>", small_style),
        ]
    ]

    for page in pages:

        page_data.append(
            [
                Paragraph(str(page.get("URL", "")), small_style),
                Paragraph(str(page.get("Status", "")), small_style),
                Paragraph(str(page.get("Title", "")), small_style),
                Paragraph(str(page.get("Issues", 0)), small_style),
            ]
        )

    page_table = Table(
        page_data,
        colWidths=[
            65 * mm,
            20 * mm,
            70 * mm,
            15 * mm,
        ],
        repeatRows=1,
    )

    page_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(page_table)

    # ---------------------------------------------------------
    # BROKEN LINKS
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "4. Broken Links",
            section_style,
        )
    )

    if broken_links:

        broken_data = [
            [
                Paragraph("<b>Page</b>", small_style),
                Paragraph("<b>Broken URL</b>", small_style),
                Paragraph("<b>Status</b>", small_style),
            ]
        ]

        for item in broken_links:

            broken_data.append(
                [
                    Paragraph(str(item.get("Page", "")), small_style),
                    Paragraph(str(item.get("url", "")), small_style),
                    Paragraph(str(item.get("status", "Error")), small_style),
                ]
            )

        broken_table = Table(
            broken_data,
            colWidths=[60 * mm, 105 * mm, 15 * mm],
            repeatRows=1,
        )

        broken_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        story.append(broken_table)

    else:

        story.append(
            Paragraph(
                "No broken links were detected in the checked pages.",
                body_style,
            )
        )

    # ---------------------------------------------------------
    # TECHNICAL
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "5. Technical SEO",
            section_style,
        )
    )

    robots = technical_files.get("robots", {})
    sitemap = technical_files.get("sitemap", {})

    technical_data = [
        ["Check", "Result"],
        [
            "robots.txt",
            "Found" if robots.get("working") else "Not Found",
        ],
        [
            "XML Sitemap",
            "Found" if sitemap.get("working") else "Not Found",
        ],
    ]

    technical_table = Table(
        technical_data,
        colWidths=[75 * mm, 95 * mm],
    )

    technical_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(technical_table)

    # ---------------------------------------------------------
    # RECOMMENDATIONS
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "6. Recommended Actions",
            section_style,
        )
    )

    recommendations = [
        r["recommendation"]
        for r in results
        if r["severity"] in ("Critical", "Warning")
    ]

    unique_recommendations = list(dict.fromkeys(recommendations))

    if unique_recommendations:

        for index, recommendation in enumerate(
            unique_recommendations,
            start=1
        ):

            story.append(
                Paragraph(
                    f"<b>{index}.</b> {recommendation}",
                    body_style,
                )
            )

    else:

        story.append(
            Paragraph(
                "No immediate corrective actions were identified.",
                body_style,
            )
        )

    # ---------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------

    def add_footer(canvas, doc):

        canvas.saveState()

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#777777"))

        canvas.drawString(
            16 * mm,
            8 * mm,
            f"{agency_name} | SEO Audit Report"
        )

        canvas.drawRightString(
            194 * mm,
            8 * mm,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_footer,
        onLaterPages=add_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()
