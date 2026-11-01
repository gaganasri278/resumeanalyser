"""PDF report generation service using ReportLab for Resume Analyser."""

import html
import io
import logging
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.resume_service import ResumeAnalysis

logger = logging.getLogger(__name__)

# Primary Design Palette: Polished Navy & Slate
COLOR_NAVY_PRIMARY = colors.HexColor("#0F172A")  # Deep Navy / Slate 900
COLOR_NAVY_SECONDARY = colors.HexColor("#1E293B")  # Slate 800
COLOR_NAVY_ACCENT = colors.HexColor("#1D4ED8")  # Royal Navy Blue
COLOR_SLATE_TEXT = colors.HexColor("#334155")  # Slate 700
COLOR_MUTED_TEXT = colors.HexColor("#64748B")  # Slate 500
COLOR_BG_LIGHT = colors.HexColor("#F8FAFC")  # Slate 50
COLOR_BORDER = colors.HexColor("#E2E8F0")  # Slate 200

# Status Indicator Colors
COLOR_PASS_BG = colors.HexColor("#ECFDF5")
COLOR_PASS_TEXT = colors.HexColor("#047857")
COLOR_WARN_BG = colors.HexColor("#FFFBEB")
COLOR_WARN_TEXT = colors.HexColor("#B45309")
COLOR_FAIL_BG = colors.HexColor("#FEF2F2")
COLOR_FAIL_TEXT = colors.HexColor("#B91C1C")
COLOR_INFO_BG = colors.HexColor("#EFF6FF")
COLOR_INFO_TEXT = colors.HexColor("#1D4ED8")

# Printable dimensions for Letter size (612 x 792 pt) with 40 pt margins
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 40.0
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2.0)  # 532.0 pt


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that dynamically calculates and renders page numbers and running headers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_header_and_footer(total_pages)
            super().showPage()
        super().save()

    def _draw_header_and_footer(self, total_pages: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_MUTED_TEXT)

        # Running Header on page 2+
        if self._pageNumber > 1:
            self.setStrokeColor(COLOR_BORDER)
            self.setLineWidth(0.6)
            self.line(MARGIN, PAGE_HEIGHT - 38, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 38)
            self.drawString(
                MARGIN, PAGE_HEIGHT - 32, "Resume Analysis & ATS Audit Report"
            )
            self.drawRightString(
                PAGE_WIDTH - MARGIN,
                PAGE_HEIGHT - 32,
                "Confidential Evaluation",
            )

        # Running Footer on all pages
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.6)
        self.line(MARGIN, 44, PAGE_WIDTH - MARGIN, 44)

        self.drawString(MARGIN, 32, "Resume Analyser — Confidential Report")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(PAGE_WIDTH - MARGIN, 32, page_str)

        self.restoreState()


def _escape(text: Any) -> str:
    """Safely escape text for ReportLab Paragraph markup."""
    if text is None:
        return ""
    escaped = html.escape(str(text))
    return escaped.replace("\n", "<br/>")


def _get_styles() -> dict[str, ParagraphStyle]:
    """Create customized typography hierarchy for the PDF report."""
    base = getSampleStyleSheet()

    styles = {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.white,
        ),
        "DocEyebrow": ParagraphStyle(
            "DocEyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#93C5FD"),
        ),
        "HeaderMeta": ParagraphStyle(
            "HeaderMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#CBD5E1"),
        ),
        "HeaderMetaRight": ParagraphStyle(
            "HeaderMetaRight",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#CBD5E1"),
            alignment=2,  # Right align
        ),
        "HeaderScoreRight": ParagraphStyle(
            "HeaderScoreRight",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#38BDF8"),
            alignment=2,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=COLOR_NAVY_PRIMARY,
            spaceBefore=12,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "SubSectionHeading": ParagraphStyle(
            "SubSectionHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=COLOR_NAVY_SECONDARY,
            spaceBefore=6,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12.5,
            textColor=COLOR_SLATE_TEXT,
            spaceAfter=4,
        ),
        "BodyBold": ParagraphStyle(
            "BodyBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12.5,
            textColor=COLOR_NAVY_PRIMARY,
            spaceAfter=4,
        ),
        "BodyMuted": ParagraphStyle(
            "BodyMuted",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11.5,
            textColor=COLOR_MUTED_TEXT,
        ),
        "CalloutText": ParagraphStyle(
            "CalloutText",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=COLOR_SLATE_TEXT,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=COLOR_SLATE_TEXT,
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=COLOR_NAVY_PRIMARY,
        ),
        "BadgePass": ParagraphStyle(
            "BadgePass",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_PASS_TEXT,
            alignment=1,  # Center
        ),
        "BadgeWarn": ParagraphStyle(
            "BadgeWarn",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_WARN_TEXT,
            alignment=1,
        ),
        "BadgeFail": ParagraphStyle(
            "BadgeFail",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_FAIL_TEXT,
            alignment=1,
        ),
    }

    return styles


def _build_header_banner(
    result: ResumeAnalysis,
    job_title: str | None,
    generation_date: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Build the top navy banner with metadata, target role, and match score."""
    target_role = (
        job_title
        or (result.job_match.target_role if result.job_match else "")
        or "General Professional Evaluation"
    )

    left_cells = [
        Paragraph("RESUME ANALYSER • CAREER INTELLIGENCE", styles["DocEyebrow"]),
        Spacer(1, 2),
        Paragraph("Resume Analysis &amp; ATS Audit Report", styles["DocTitle"]),
        Spacer(1, 4),
        Paragraph(
            f"Target Role: <b>{_escape(target_role)}</b>",
            styles["HeaderMeta"],
        ),
    ]

    right_cells = [
        Paragraph(
            f"Date: <b>{_escape(generation_date)}</b>", styles["HeaderMetaRight"]
        ),
        Spacer(1, 2),
        Paragraph(
            f"Engine: <b>{_escape(result.analysis_mode)}</b>",
            styles["HeaderMetaRight"],
        ),
    ]

    if result.job_match is not None and result.job_match.match_score > 0:
        right_cells.extend(
            [
                Spacer(1, 3),
                Paragraph(
                    f"{result.job_match.match_score}% Match Alignment",
                    styles["HeaderScoreRight"],
                ),
            ]
        )

    banner_data = [[left_cells, right_cells]]
    col_w1 = CONTENT_WIDTH * 0.65
    col_w2 = CONTENT_WIDTH * 0.35

    banner_table = Table(banner_data, colWidths=[col_w1, col_w2])
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_NAVY_PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return banner_table


def _build_warnings_block(
    warnings: list[str], styles: dict[str, ParagraphStyle]
) -> Table | None:
    """Build a highlighted callout table if critical warnings exist."""
    if not warnings:
        return None

    warning_paragraphs = [
        Paragraph("<b>Important Document Warnings:</b>", styles["TableCellBold"]),
        Spacer(1, 2),
    ]
    for w in warnings:
        warning_paragraphs.append(Paragraph(f"• {_escape(w)}", styles["CalloutText"]))

    t = Table([[warning_paragraphs]], colWidths=[CONTENT_WIDTH])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_WARN_BG),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_WARN_TEXT),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def _build_match_score_card(
    result: ResumeAnalysis, styles: dict[str, ParagraphStyle]
) -> Table | None:
    """Build role match assessment and methodology breakdown card."""
    match = result.job_match
    if match is None:
        return None

    content = [
        Paragraph(
            f"<b>Role Alignment Assessment: {match.match_score}% Coverage</b>",
            styles["BodyBold"],
        ),
        Paragraph(
            _escape(match.fit_summary) or "Fit assessment not provided.",
            styles["Body"],
        ),
        Spacer(1, 3),
        Paragraph(
            f"<b>Scoring Methodology &amp; Evidence:</b> "
            f"{_escape(match.match_score_explanation or 'Calculated based on detected skills, qualification requirements, and experience relevance. Represents alignment, not a subjective hiring guarantee.')}",
            styles["BodyMuted"],
        ),
    ]

    card = Table([[content]], colWidths=[CONTENT_WIDTH])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
                ("LINELEFT", (0, 0), (-1, -1), 3, COLOR_NAVY_ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return card


def _build_skills_matrix(
    result: ResumeAnalysis, styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Build the skills matrix with matched, missing, evidenced, and technical skills."""
    elements: list[Any] = []
    match = result.job_match

    if match is not None:
        # 3 columns: Matched, Missing, Insufficiently Evidenced
        matched_str = (
            ", ".join(_escape(s) for s in match.matching_skills)
            if match.matching_skills
            else "None identified"
        )
        missing_str = (
            ", ".join(_escape(s) for s in match.missing_skills)
            if match.missing_skills
            else "None detected"
        )
        evidenced_str = (
            ", ".join(_escape(s) for s in match.insufficiently_evidenced_skills)
            if match.insufficiently_evidenced_skills
            else "None flagged"
        )

        col_w = CONTENT_WIDTH / 3.0
        data = [
            [
                Paragraph("<b>[Matched Required Skills]</b>", styles["TableCellBold"]),
                Paragraph("<b>[Missing Core Skills]</b>", styles["TableCellBold"]),
                Paragraph("<b>[Needs More Evidence]</b>", styles["TableCellBold"]),
            ],
            [
                Paragraph(matched_str, styles["TableCell"]),
                Paragraph(missing_str, styles["TableCell"]),
                Paragraph(evidenced_str, styles["TableCell"]),
            ],
        ]
        t = Table(data, colWidths=[col_w, col_w, col_w])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), COLOR_PASS_BG),
                    ("BACKGROUND", (1, 0), (1, 0), COLOR_FAIL_BG),
                    ("BACKGROUND", (2, 0), (2, 0), COLOR_WARN_BG),
                    ("BACKGROUND", (0, 1), (-1, 1), COLOR_BG_LIGHT),
                    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 6))

    # Technical & Soft skills lists
    tech_str = (
        ", ".join(_escape(s) for s in result.technical_skills)
        if result.technical_skills
        else "Not provided"
    )
    soft_str = (
        ", ".join(_escape(s) for s in result.soft_skills)
        if result.soft_skills
        else "Not provided"
    )

    skills_data = [
        [
            Paragraph("<b>Identified Technical Skills:</b>", styles["TableCellBold"]),
            Paragraph(tech_str, styles["TableCell"]),
        ],
        [
            Paragraph(
                "<b>Transferable &amp; Soft Skills:</b>", styles["TableCellBold"]
            ),
            Paragraph(soft_str, styles["TableCell"]),
        ],
    ]
    st_table = Table(skills_data, colWidths=[140, CONTENT_WIDTH - 140])
    st_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(st_table)
    return elements


def _build_ats_checks_table(
    result: ResumeAnalysis, styles: dict[str, ParagraphStyle]
) -> Table | Paragraph:
    """Build structured table of ATS readability and formatting checks."""
    if not result.ats_formatting_checks:
        return Paragraph("No ATS formatting checks recorded.", styles["BodyMuted"])

    col_w_name = 120.0
    col_w_status = 65.0
    col_w_findings = CONTENT_WIDTH - col_w_name - col_w_status

    header_row = [
        Paragraph("<b>Audit Check</b>", styles["TableCellBold"]),
        Paragraph("<b>Status</b>", styles["TableCellBold"]),
        Paragraph("<b>Findings &amp; Recommendation</b>", styles["TableCellBold"]),
    ]

    rows = [header_row]
    table_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_NAVY_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]

    for i, check in enumerate(result.ats_formatting_checks, start=1):
        if check.status == "pass":
            status_p = Paragraph("PASS", styles["BadgePass"])
            bg_badge = COLOR_PASS_BG
        elif check.status == "warning":
            status_p = Paragraph("WARNING", styles["BadgeWarn"])
            bg_badge = COLOR_WARN_BG
        else:
            status_p = Paragraph("ATTENTION", styles["BadgeFail"])
            bg_badge = COLOR_FAIL_BG

        finding_text = f"<b>Finding:</b> {_escape(check.finding)}"
        if check.suggestion:
            finding_text += f"<br/><b>Recommendation:</b> {_escape(check.suggestion)}"

        rows.append(
            [
                Paragraph(_escape(check.check_name), styles["TableCellBold"]),
                status_p,
                Paragraph(finding_text, styles["TableCell"]),
            ]
        )

        table_styles.append(("BACKGROUND", (1, i), (1, i), bg_badge))
        if i % 2 == 0:
            table_styles.append(("BACKGROUND", (0, i), (0, i), COLOR_BG_LIGHT))
            table_styles.append(("BACKGROUND", (2, i), (2, i), COLOR_BG_LIGHT))

    t = Table(rows, colWidths=[col_w_name, col_w_status, col_w_findings], repeatRows=1)
    t.setStyle(TableStyle(table_styles))
    return t


def _build_bullet_rewrites(
    result: ResumeAnalysis, styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Build bullet point improvements with STAR framework."""
    if not result.bullet_point_improvements:
        return [
            Paragraph(
                "No specific bullet point revisions required. Bullet statements appear well structured.",
                styles["BodyMuted"],
            )
        ]

    elements: list[Any] = []
    for item in result.bullet_point_improvements:
        card_content = [
            Paragraph(
                f"<b>Original / Identified Weakness:</b><br/>"
                f"<font color='{COLOR_FAIL_TEXT.hexval()}'>{_escape(item.original_or_issue)}</font>",
                styles["TableCell"],
            ),
            Spacer(1, 2),
            Paragraph(
                f"<b>Suggested STAR Revision:</b><br/>"
                f"<font color='{COLOR_PASS_TEXT.hexval()}'><b>{_escape(item.suggested_revision)}</b></font>",
                styles["TableCell"],
            ),
            Spacer(1, 2),
            Paragraph(
                f"<b>Why this works:</b> {_escape(item.explanation)}",
                styles["BodyMuted"],
            ),
        ]

        t = Table([[card_content]], colWidths=[CONTENT_WIDTH])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("LINELEFT", (0, 0), (-1, -1), 2.5, COLOR_PASS_TEXT),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 5))

    return elements


def _build_action_plan(
    result: ResumeAnalysis, styles: dict[str, ParagraphStyle]
) -> Table | Paragraph:
    """Build prioritized action plan table."""
    if not result.prioritized_action_plan:
        return Paragraph("No prioritized action items generated.", styles["BodyMuted"])

    col_w_pri = 60.0
    col_w_action = 322.0
    col_w_impact = CONTENT_WIDTH - col_w_pri - col_w_action

    header_row = [
        Paragraph("<b>Priority</b>", styles["TableCellBold"]),
        Paragraph("<b>Action &amp; Guidance</b>", styles["TableCellBold"]),
        Paragraph("<b>Expected Impact</b>", styles["TableCellBold"]),
    ]
    rows = [header_row]

    table_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_NAVY_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]

    for i, item in enumerate(result.prioritized_action_plan, start=1):
        if item.priority == "High":
            badge_p = Paragraph("HIGH", styles["BadgeFail"])
            bg_badge = COLOR_FAIL_BG
        elif item.priority == "Medium":
            badge_p = Paragraph("MEDIUM", styles["BadgeWarn"])
            bg_badge = COLOR_WARN_BG
        else:
            badge_p = Paragraph("LOW", styles["BadgePass"])
            bg_badge = COLOR_PASS_BG

        action_text = f"<b>{_escape(item.title)}</b><br/>{_escape(item.action)}"
        rows.append(
            [
                badge_p,
                Paragraph(action_text, styles["TableCell"]),
                Paragraph(_escape(item.impact), styles["TableCell"]),
            ]
        )

        table_styles.append(("BACKGROUND", (0, i), (0, i), bg_badge))
        if i % 2 == 0:
            table_styles.append(("BACKGROUND", (1, i), (1, i), COLOR_BG_LIGHT))
            table_styles.append(("BACKGROUND", (2, i), (2, i), COLOR_BG_LIGHT))

    t = Table(rows, colWidths=[col_w_pri, col_w_action, col_w_impact], repeatRows=1)
    t.setStyle(TableStyle(table_styles))
    return t


def generate_resume_pdf_report(
    result: ResumeAnalysis,
    *,
    job_title: str | None = None,
    generation_date: str | None = None,
) -> bytes:
    """Generate a high-quality PDF report from resume analysis results.

    Parameters
    ----------
    result: ResumeAnalysis
        The validated resume analysis result model.
    job_title: str | None
        Optional target job title to display in report header.
    generation_date: str | None
        Optional date string. If omitted, uses current formatted date.

    Returns
    -------
    bytes:
        Binary PDF data ready for download.
    """
    if not generation_date:
        generation_date = datetime.now(UTC).strftime("%B %d, %Y")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 12,
        bottomMargin=MARGIN + 12,
    )

    styles = _get_styles()
    story: list[Any] = []

    # 1. Top Header Banner
    story.append(_build_header_banner(result, job_title, generation_date, styles))
    story.append(Spacer(1, 8))

    # 2. Critical Document Warnings (if any)
    warnings_block = _build_warnings_block(result.warnings, styles)
    if warnings_block is not None:
        story.append(warnings_block)
        story.append(Spacer(1, 8))

    # 3. Role Match Assessment Card (if job match performed)
    match_card = _build_match_score_card(result, styles)
    if match_card is not None:
        story.append(match_card)
        story.append(Spacer(1, 8))

    # 4. Executive Summary
    story.append(Paragraph("1. Executive Resume Summary", styles["SectionHeading"]))
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=COLOR_NAVY_PRIMARY, spaceAfter=5)
    )
    summary_text = _escape(result.resume_summary) or "Not provided."
    story.append(Paragraph(summary_text, styles["Body"]))
    story.append(Spacer(1, 6))

    # 5. Skills Matrix & Requirement Alignment
    story.append(
        Paragraph(
            "2. Skills Matrix &amp; Requirement Alignment", styles["SectionHeading"]
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=COLOR_NAVY_PRIMARY, spaceAfter=5)
    )
    story.extend(_build_skills_matrix(result, styles))
    story.append(Spacer(1, 6))

    # 6. Career Trajectory & Experience Relevance
    story.append(
        Paragraph("3. Experience &amp; Project Relevance", styles["SectionHeading"])
    )
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=COLOR_NAVY_PRIMARY, spaceAfter=5)
    )
    exp_text = _escape(result.experience_assessment) or "Not provided."
    story.append(Paragraph(exp_text, styles["Body"]))

    if result.job_match is not None:
        match = result.job_match
        if match.experience_relevance:
            story.append(
                Paragraph(
                    f"<b>Experience Relevance:</b> {_escape(match.experience_relevance)}",
                    styles["Body"],
                )
            )
        if match.project_relevance:
            story.append(
                Paragraph(
                    f"<b>Project Relevance:</b> {_escape(match.project_relevance)}",
                    styles["Body"],
                )
            )
        if match.strengths:
            story.append(Paragraph("<b>Candidate Strengths:</b>", styles["BodyBold"]))
            for s in match.strengths:
                story.append(Paragraph(f"• {_escape(s)}", styles["Body"]))
        recs = match.role_recommendations or match.improvement_suggestions
        if recs:
            story.append(
                Paragraph("<b>Role Tailoring Recommendations:</b>", styles["BodyBold"])
            )
            for r in recs:
                story.append(Paragraph(f"• {_escape(r)}", styles["Body"]))

    story.append(Spacer(1, 6))

    # 7. ATS Readability & Formatting Checks
    story.append(
        Paragraph("4. ATS Readability &amp; Formatting Audit", styles["SectionHeading"])
    )
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=COLOR_NAVY_PRIMARY, spaceAfter=5)
    )
    story.append(_build_ats_checks_table(result, styles))
    story.append(Spacer(1, 6))

    # 8. Bullet Point Rewrites (STAR Methodology)
    story.append(
        Paragraph(
            "5. High-Impact Bullet Point Rewrites (STAR Framework)",
            styles["SectionHeading"],
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=COLOR_NAVY_PRIMARY, spaceAfter=5)
    )
    story.extend(_build_bullet_rewrites(result, styles))
    story.append(Spacer(1, 6))

    # 9. Prioritized Action Plan
    story.append(Paragraph("6. Prioritized Action Plan", styles["SectionHeading"]))
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=COLOR_NAVY_PRIMARY, spaceAfter=5)
    )
    story.append(_build_action_plan(result, styles))

    # Build PDF with dynamic multi-page NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def export_analysis_json(result: ResumeAnalysis) -> str:
    """Retain internal JSON serialization capability."""
    return result.model_dump_json(indent=2)
