"""Reusable UI components for Resume Analyser."""

import html
import logging

import streamlit as st

from app.config.settings import Settings
from app.integrations.ai_provider import GeminiResumeProvider
from app.services.pdf_report_service import generate_resume_pdf_report
from app.services.resume_service import (
    ActionItem,
    ATSCheckItem,
    BulletPointImprovement,
    ResumeAnalysis,
)

logger = logging.getLogger(__name__)


def render_sidebar(settings: Settings) -> str:
    """Render professional sidebar branding, navigation, and Gemini connection probe."""
    with st.sidebar:
        st.markdown(
            """
            <div class="ra-brand-header">
                <div class="ra-brand-logo">R</div>
                <div>
                    <div class="ra-brand-title">Resume Analyser</div>
                    <div class="ra-brand-tagline">AI Career Intelligence</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("NAVIGATION")
        section = st.radio(
            "Application sections",
            ["Dashboard", "Resume Analysis", "About"],
            label_visibility="collapsed",
            key="active_section",
        )

        st.divider()

        st.caption("AI ENGINE CONFIGURATION")
        has_key = bool(settings.gemini_api_key.strip())
        if has_key:
            st.success(f"Google Gemini configured ({settings.gemini_model})", icon="✅")
        else:
            st.warning("GEMINI_API_KEY is not configured.", icon="⚠️")
            st.caption(
                "Add your key to `.env` or Streamlit secrets (`GEMINI_API_KEY`). "
                "Local mode remains available without an API key."
            )

        if st.button(
            "Verify Gemini Connection",
            use_container_width=True,
            help="Test API key with a safe ping",
        ):
            fresh_settings = Settings.from_env()
            if not fresh_settings.gemini_api_key.strip():
                st.error(
                    "Cannot test: GEMINI_API_KEY is not configured in .env or secrets."
                )
            else:
                with st.spinner(
                    f"Testing connection to Google Gemini ({fresh_settings.gemini_model})..."
                ):
                    try:
                        provider = GeminiResumeProvider(fresh_settings)
                        success, message = provider.test_connection()
                        if success:
                            st.success(message)
                        elif (
                            "503" in message
                            or "504" in message
                            or "High Demand" in message
                        ):
                            st.warning(message)
                        else:
                            st.error(message)
                    except Exception as exc:
                        st.error(f"Connection test failed: {exc}")

        st.divider()
        st.caption(
            "Privacy: Resume text is processed in-memory. In Gemini mode, data is sent to Google only with your explicit consent."
        )
        return section


def render_page_heading(
    title: str,
    eyebrow: str,
    subtitle: str,
    introduction: str,
) -> None:
    """Render page hero section with consistent typography."""
    st.markdown(
        f"""
        <div class="ra-hero-container">
            <span class="ra-hero-eyebrow">{html.escape(eyebrow)}</span>
            <h1 class="ra-hero-heading">{html.escape(title)}</h1>
            <p class="ra-hero-subtitle">{html.escape(subtitle)}</p>
            <p style="color: var(--ra-slate-500); font-size: 0.95rem; margin-top: 0.5rem; max-width: 780px; line-height: 1.6;">
                {html.escape(introduction)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_overview() -> None:
    """Render key capability overview cards."""
    features = [
        (
            "🎯 ATS & Keyword Audit",
            "Evaluate standard section headers, density, contact information, and parseability for ATS systems.",
        ),
        (
            "📊 Role Match & Skill Matrix",
            "Evidence-based comparison against your target job title and description, identifying matched vs missing skills.",
        ),
        (
            "✍️ STAR Bullet Revisions",
            "Actionable recommendations to rewrite weak bullets into high-impact, quantified achievement statements.",
        ),
    ]

    cols = st.columns(3)
    for col, (title, desc) in zip(cols, features, strict=True):
        with col:
            st.markdown(
                f"""
                <div class="ra-card">
                    <div class="ra-card-title">{html.escape(title)}</div>
                    <p class="ra-card-desc">{html.escape(desc)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_empty_state() -> None:
    """Render helpful instructions when no analysis has been run yet."""
    st.markdown(
        """
        <div class="ra-card" style="margin-top: 1.5rem; border-style: dashed;">
            <div class="ra-card-title">🚀 Ready for Analysis</div>
            <p class="ra-card-desc">
                Follow these simple steps to analyze your resume:
            </p>
            <ol style="color: var(--ra-slate-600); font-size: 0.9rem; line-height: 1.8; margin-top: 0.75rem; padding-left: 1.25rem;">
                <li><strong>Upload your document:</strong> Choose a PDF or DOCX file (up to 5 MB), or paste your resume text.</li>
                <li><strong>Target role (recommended):</strong> Enter the job title and paste the job description to compare skills and requirements.</li>
                <li><strong>Consent & Submit:</strong> Confirm consent for Google Gemini processing and click <em>Analyse Resume</em>.</li>
                <li><strong>Action your feedback:</strong> Review your match score, ATS checks, bullet rewrites, and prioritized action plan.</li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_pill_list(items: list[str], pill_class: str) -> None:
    """Render an array of strings as styled pill badges."""
    if not items:
        st.caption("None identified.")
        return

    pills_html = "".join(
        f'<span class="ra-pill {pill_class}">{html.escape(item)}</span>'
        for item in items
    )
    st.markdown(
        f'<div style="margin: 0.4rem 0 0.8rem;">{pills_html}</div>',
        unsafe_allow_html=True,
    )


def _render_bullet_improvements(improvements: list[BulletPointImprovement]) -> None:
    """Render before-and-after bullet rewrites using the STAR methodology."""
    st.markdown("### ✍️ High-Impact Bullet Point Rewrites")
    st.caption(
        "Transform passive tasks into quantified, achievement-oriented bullets (STAR framework)."
    )

    if not improvements:
        st.info(
            "No specific bullet point revisions required. Bullet statements appear well structured."
        )
        return

    for item in improvements:
        st.markdown(
            f"""
            <div class="ra-bullet-box">
                <div style="font-size: 0.82rem; font-weight: 700; color: var(--ra-slate-500); text-transform: uppercase; margin-bottom: 0.25rem;">Original / Identified Weakness:</div>
                <div class="ra-bullet-original">{html.escape(item.original_or_issue)}</div>
                <div style="font-size: 0.82rem; font-weight: 700; color: #065F46; text-transform: uppercase; margin-bottom: 0.25rem;">Suggested STAR Revision:</div>
                <div class="ra-bullet-suggested">{html.escape(item.suggested_revision)}</div>
                <div class="ra-bullet-why">💡 <strong>Why this works:</strong> {html.escape(item.explanation)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_ats_checks(checks: list[ATSCheckItem]) -> None:
    """Render detailed ATS formatting and readability inspection findings."""
    st.markdown("### 🔍 ATS Readability & Formatting Checks")
    st.caption(
        "Applicant Tracking System scan checking for standard headings, density, and parseability."
    )

    if not checks:
        st.caption("No ATS checks available.")
        return

    for check in checks:
        if check.status == "pass":
            badge = '<span class="ra-pill ra-pill-green">✓ Pass</span>'
        elif check.status == "warning":
            badge = '<span class="ra-pill ra-pill-amber">⚠ Warning</span>'
        else:
            badge = '<span class="ra-pill ra-pill-red">✗ Attention Needed</span>'

        st.markdown(
            f"""
            <div class="ra-card" style="margin-bottom: 0.75rem; padding: 1rem 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                    <strong style="color: var(--ra-slate-900); font-size: 0.95rem;">{html.escape(check.check_name)}</strong>
                    {badge}
                </div>
                <div style="font-size: 0.88rem; color: var(--ra-slate-700); margin-bottom: 0.3rem;">
                    {html.escape(check.finding)}
                </div>
                <div style="font-size: 0.82rem; color: var(--ra-slate-500);">
                    💡 <em>Recommendation:</em> {html.escape(check.suggestion)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_action_plan(items: list[ActionItem]) -> None:
    """Render prioritized action items (High, Medium, Low)."""
    st.markdown("### 📋 Prioritized Action Plan")
    st.caption(
        "Focus on high-impact updates first to maximize recruiter and ATS response rates."
    )

    if not items:
        st.caption("No action items generated.")
        return

    for item in items:
        priority_class = f"priority-{item.priority.lower()}"
        pill_class = (
            "ra-pill-red"
            if item.priority == "High"
            else "ra-pill-amber"
            if item.priority == "Medium"
            else "ra-pill-blue"
        )

        st.markdown(
            f"""
            <div class="ra-action-item {priority_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                    <strong style="color: var(--ra-slate-900); font-size: 1rem;">{html.escape(item.title)}</strong>
                    <span class="ra-pill {pill_class}">{html.escape(item.priority)} Priority</span>
                </div>
                <p style="font-size: 0.9rem; color: var(--ra-slate-700); margin: 0 0 0.4rem; line-height: 1.5;">
                    {html.escape(item.action)}
                </p>
                <div style="font-size: 0.82rem; color: var(--ra-slate-500);">
                    🎯 <strong>Expected Impact:</strong> {html.escape(item.impact)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_analysis(result: ResumeAnalysis, job_title: str | None = None) -> None:
    """Render comprehensive, professional analysis results."""
    st.markdown("---")
    st.caption(f"Analysis Provider: {result.analysis_mode}")

    # Critical warnings if any
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning, icon="⚠️")

    # Match score banner if job match was performed
    if result.job_match is not None:
        match = result.job_match
        role_label = match.target_role or "Target Role"
        score = match.match_score

        st.markdown(
            f"""
            <div class="ra-score-card">
                <div class="ra-score-label">Role Alignment Assessment • {html.escape(role_label)}</div>
                <div style="display: flex; align-items: baseline; gap: 0.5rem;">
                    <span class="ra-score-number">{score}%</span>
                    <span style="font-size: 1.1rem; color: #93C5FD; font-weight: 600;">Match Alignment</span>
                </div>
                <div style="font-size: 1rem; margin-top: 0.5rem; color: #FFFFFF; font-weight: 500;">
                    {html.escape(match.fit_summary)}
                </div>
                <div class="ra-score-explanation">
                    <strong>Score Breakdown & Methodology:</strong> {html.escape(match.match_score_explanation or "Calculated based on matched required core skills, technical overlap, and experience relevance. This is an alignment indicator, not an objective hiring guarantee.")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "💡 Add a target role title and job description to unlock job-specific match scoring and skill gap analysis."
        )

    # Executive Overview
    overview_col1, overview_col2 = st.columns(2)
    with overview_col1:
        with st.container(border=True):
            st.markdown("#### 📄 Executive Resume Summary")
            st.write(result.resume_summary or "No summary available.")
    with overview_col2:
        with st.container(border=True):
            st.markdown("#### 💼 Career Trajectory & Experience")
            st.write(
                result.experience_assessment or "No experience assessment available."
            )

    # Skills Matrix
    st.markdown("### 🧩 Skills Matrix")
    if result.job_match is not None:
        match = result.job_match
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            with st.container(border=True):
                st.markdown("##### ✅ Matched Required Skills")
                _render_pill_list(match.matching_skills, "ra-pill-green")
        with s_col2:
            with st.container(border=True):
                st.markdown("##### ❌ Missing Core Skills")
                _render_pill_list(match.missing_skills, "ra-pill-red")
        with s_col3:
            with st.container(border=True):
                st.markdown("##### ⚠️ Needs More Evidence")
                _render_pill_list(
                    match.insufficiently_evidenced_skills, "ra-pill-amber"
                )

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        with st.container(border=True):
            st.markdown("##### 💻 Identified Technical Skills")
            _render_pill_list(result.technical_skills, "ra-pill-blue")
    with t_col2:
        with st.container(border=True):
            st.markdown("##### 🤝 Transferable & Soft Skills")
            _render_pill_list(result.soft_skills, "ra-pill-blue")

    # Role alignment details if job match exists
    if result.job_match is not None:
        match = result.job_match
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            with st.container(border=True):
                st.markdown("##### 🎯 Experience Alignment")
                st.write(
                    match.experience_relevance
                    or "Analysis of role experience alignment."
                )
                if match.strengths:
                    st.markdown("**Key Candidate Strengths:**")
                    for s in match.strengths:
                        st.markdown(f"- {s}")
        with r_col2:
            with st.container(border=True):
                st.markdown("##### 🛠️ Project Alignment & Role Recommendations")
                st.write(
                    match.project_relevance or "Analysis of project stack alignment."
                )
                recs = match.role_recommendations or match.improvement_suggestions
                if recs:
                    st.markdown("**Role-Specific Tailoring Suggestions:**")
                    for r in recs:
                        st.markdown(f"- {r}")

    # Bullet point rewrites
    if result.bullet_point_improvements:
        _render_bullet_improvements(result.bullet_point_improvements)

    # ATS Checks
    if result.ats_formatting_checks:
        _render_ats_checks(result.ats_formatting_checks)

    # Prioritized Action Plan
    if result.prioritized_action_plan:
        _render_action_plan(result.prioritized_action_plan)

    # Download Full Analysis Report (PDF)
    st.markdown("---")
    resolved_job_title = (
        job_title or (result.job_match.target_role if result.job_match else "") or None
    )
    try:
        pdf_bytes = generate_resume_pdf_report(
            result,
            job_title=resolved_job_title,
        )
        st.download_button(
            "📥 Download Full Analysis Report (PDF)",
            data=pdf_bytes,
            file_name="resume-analysis-report.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    except Exception as exc:
        logger.error("Failed to generate PDF report: %s", exc, exc_info=True)
        st.error(f"Could not generate PDF report: {exc}")
