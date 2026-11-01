"""Streamlit application entry point for Resume Analyser."""

import logging
from uuid import uuid4

import streamlit as st

from app.config.settings import Settings
from app.integrations.ai_provider import (
    AIProviderError,
    create_resume_provider,
)
from app.services.local_resume_service import LocalResumeAnalyzer
from app.services.resume_service import (
    ResumeAnalysis,
    ResumeAnalysisError,
    ResumeService,
)
from app.ui.components import (
    render_analysis,
    render_empty_state,
    render_feature_overview,
    render_page_heading,
    render_sidebar,
)
from app.ui.theme import apply_theme
from app.utils.logging_config import configure_logging
from app.utils.rate_limiter import AnalysisRateLimiter
from app.utils.resume_parser import ResumeParseError, extract_resume_text

logger = logging.getLogger(__name__)

GEMINI_MODE = "Google Gemini (Recommended)"
LOCAL_MODE = "Local keyword-based (Offline / Fallback)"


@st.cache_resource
def get_rate_limiter(
    max_requests: int,
    max_concurrent: int,
) -> AnalysisRateLimiter:
    """Share the process-local rate limiter across Streamlit sessions."""
    return AnalysisRateLimiter(max_requests, max_concurrent)


def clear_analysis() -> None:
    """Clear current analysis results and inputs from session state."""
    st.session_state.pop("resume_analysis", None)
    st.session_state.pop("analysis_request_id", None)
    st.session_state.pop("pending_local_analysis", None)
    st.session_state["resume_text"] = ""
    st.session_state["job_title"] = ""
    st.session_state["job_description"] = ""
    st.session_state["gemini_consent"] = False
    st.session_state["resume_upload_version"] = (
        st.session_state.get("resume_upload_version", 0) + 1
    )


def render_workspace(settings: Settings) -> None:
    """Render resume input form, job description, and trigger analysis."""
    st.markdown("### 📝 Analysis Workspace")
    st.caption(
        "Upload your resume or paste its text. Add target role details for evidence-based matching."
    )

    # Re-read fresh settings to capture any recent .env edits
    current_settings = Settings.from_env()
    has_gemini_key = bool(current_settings.gemini_api_key.strip())
    mode_options = (
        [GEMINI_MODE, LOCAL_MODE] if has_gemini_key else [LOCAL_MODE, GEMINI_MODE]
    )

    analysis_mode = st.selectbox(
        "Analysis engine",
        mode_options,
        index=0,
        key="analysis_mode",
        help=(
            "Google Gemini delivers comprehensive semantic matching, ATS audits, and bullet point rewrites. "
            "Local mode performs deterministic keyword and pattern matching on your machine without external API calls."
        ),
    )

    if analysis_mode == GEMINI_MODE and not has_gemini_key:
        st.warning(
            "⚠️ GEMINI_API_KEY is not configured. Please add your key to `.env` or Streamlit secrets, "
            "or switch to Local mode for immediate offline analysis."
        )

    with st.container(border=True):
        with st.form("resume_analysis_form"):
            uploaded_resume = st.file_uploader(
                "Upload Resume Document (PDF or DOCX, max 5 MB)",
                type=["pdf", "docx"],
                key=f"resume_upload_{st.session_state.get('resume_upload_version', 0)}",
                help="Text-based PDFs and DOCX files are supported. Scanned images require OCR and are not supported.",
            )

            resume_col, job_col = st.columns(2)
            with resume_col:
                resume_text = st.text_area(
                    "Or paste resume text",
                    height=200,
                    max_chars=settings.max_resume_chars,
                    placeholder="Paste plain text resume content here...",
                    key="resume_text",
                )

            with job_col:
                job_title = st.text_input(
                    "Target job title (optional)",
                    placeholder="e.g. Senior Software Engineer",
                    key="job_title",
                )
                job_description = st.text_area(
                    "Job description / requirements (optional)",
                    height=148,
                    max_chars=settings.max_resume_chars,
                    placeholder="Paste job description or core requirements...",
                    key="job_description",
                )

            consent = False
            if analysis_mode == GEMINI_MODE:
                consent = st.checkbox(
                    "I consent to sending this resume and job description to Google Gemini for AI analysis. "
                    "I understand that the text may contain personal data.",
                    key="gemini_consent",
                )
            else:
                st.caption(
                    "🔒 Local mode stays strictly within this application. No text is sent externally."
                )

            submitted = st.form_submit_button(
                "Analyse Resume",
                type="primary",
                use_container_width=True,
            )

    clear_col, info_col = st.columns([1, 3])
    with clear_col:
        st.button(
            "Clear inputs and report",
            on_click=clear_analysis,
            use_container_width=True,
        )
    with info_col:
        if analysis_mode == GEMINI_MODE:
            st.caption(
                "Google Gemini processes text only upon submission with your consent. No resume data is stored."
            )
        else:
            st.caption(
                "Local mode runs entirely offline in this Python process. No network requests are made."
            )

    if submitted:
        st.session_state.pop("resume_analysis", None)
        st.session_state.pop("analysis_request_id", None)
        st.session_state.pop("pending_local_analysis", None)

        analysis_text = resume_text.strip()
        input_error = False

        try:
            if uploaded_resume is not None and analysis_text:
                raise ResumeParseError(
                    "Please either upload a resume file or paste text, not both."
                )
            if uploaded_resume is not None:
                analysis_text = extract_resume_text(
                    uploaded_resume.name,
                    uploaded_resume.getvalue(),
                    max_text_chars=settings.max_resume_chars,
                )
        except ResumeParseError as exc:
            st.error(str(exc))
            input_error = True

        if not input_error and not analysis_text:
            st.error(
                "Please upload a PDF/DOCX resume or paste resume text before submitting."
            )
        elif not input_error and analysis_mode == GEMINI_MODE and not consent:
            st.error("Consent is required before sending resume data to Google Gemini.")
        elif not input_error and analysis_mode == LOCAL_MODE:
            try:
                result = LocalResumeAnalyzer(settings.max_resume_chars).analyze(
                    analysis_text,
                    job_description=job_description,
                    job_title=job_title,
                )
                st.session_state["resume_analysis"] = result
                st.session_state["analysis_request_id"] = None
                logger.info(
                    "Local keyword-based resume analysis completed successfully."
                )
            except ResumeAnalysisError as exc:
                st.error(str(exc))
        elif not input_error:
            # Gemini Mode
            limiter = get_rate_limiter(
                current_settings.max_analyses_per_minute,
                current_settings.max_concurrent_analyses,
            )
            if not limiter.try_acquire():
                st.warning(
                    "Analysis capacity is temporarily busy. Please wait a few seconds and try again."
                )
            else:
                request_id = uuid4().hex
                try:
                    provider = create_resume_provider(current_settings)
                    service = ResumeService(current_settings, provider=provider)

                    with st.spinner(
                        "Analyzing resume structure, ATS alignment, and role fit with Google Gemini..."
                    ):
                        result = service.analyze(
                            analysis_text,
                            request_id=request_id,
                            job_description=job_description,
                            job_title=job_title,
                        )

                    st.session_state["resume_analysis"] = result
                    st.session_state["analysis_request_id"] = request_id
                    logger.info(
                        "Gemini resume analysis completed; request_id=%s", request_id
                    )
                except AIProviderError as exc:
                    logger.warning(
                        "AI provider error; request_id=%s error=%s", request_id, exc
                    )
                    st.error(str(exc))
                    if exc.local_fallback_available:
                        st.session_state["pending_local_analysis"] = {
                            "resume_text": analysis_text,
                            "job_description": job_description,
                            "job_title": job_title,
                        }
                except ResumeAnalysisError as exc:
                    logger.warning(
                        "Resume analysis error; request_id=%s error=%s", request_id, exc
                    )
                    st.error(str(exc))
                    if exc.local_fallback_available:
                        st.session_state["pending_local_analysis"] = {
                            "resume_text": analysis_text,
                            "job_description": job_description,
                            "job_title": job_title,
                        }
                except Exception as exc:
                    logger.error(
                        "Unexpected analysis failure; request_id=%s error_type=%s",
                        request_id,
                        type(exc).__name__,
                    )
                    st.error(
                        f"Analysis could not be completed. Reference ID: {request_id[:8]}"
                    )
                finally:
                    limiter.release()

    # Offer local fallback if API quota or connection issue occurred
    pending = st.session_state.get("pending_local_analysis")
    if pending:
        st.info(
            "⚠️ Gemini API was unavailable due to quota, rate limits, or network connectivity. You can run immediate local analysis instead:"
        )
        if st.button("Run Local Keyword Analysis Instead", key="btn_local_fallback"):
            try:
                result = LocalResumeAnalyzer(settings.max_resume_chars).analyze(
                    pending["resume_text"],
                    job_description=pending.get("job_description"),
                    job_title=pending.get("job_title"),
                )
                st.session_state["resume_analysis"] = result
                st.session_state["analysis_request_id"] = None
                st.session_state.pop("pending_local_analysis", None)
                st.rerun()
            except ResumeAnalysisError as exc:
                st.error(str(exc))

    # Render analysis or empty state guide
    current_result = st.session_state.get("resume_analysis")
    if isinstance(current_result, ResumeAnalysis):
        target_job_title = st.session_state.get("job_title", "").strip() or None
        render_analysis(current_result, job_title=target_job_title)
    else:
        render_empty_state()


def render_about() -> None:
    """Render About section detailing privacy, methodology, and capabilities."""
    render_page_heading(
        title="About Resume Analyser",
        eyebrow="TRANSPARENCY & METHODOLOGY",
        subtitle="Practical, evidence-grounded resume intelligence for modern job applications.",
        introduction=(
            "Resume Analyser evaluates resumes against Applicant Tracking System (ATS) guidelines "
            "and target job descriptions to provide objective, actionable feedback."
        ),
    )

    with st.container(border=True):
        st.markdown("#### 🔒 Privacy & Data Handling")
        st.write(
            "Your privacy is our priority. In **Local Mode**, text processing runs 100% offline within this Python process. "
            "In **Google Gemini Mode**, your resume text is sent securely to the Google Gemini API only after you explicitly grant consent. "
            "Uploaded resumes are processed in-memory and are never permanently stored, indexed, or shared."
        )

    with st.container(border=True):
        st.markdown("#### 📊 Analysis Scope & Score Explanation")
        st.write(
            "• **ATS Audit:** Reviews section headings, contact information, text density, and bullet point structure.\n"
            "• **Skill Gap Analysis:** Extracts required technical and soft skills from job descriptions and compares them with evidence in your resume.\n"
            "• **STAR Bullet Revisions:** Suggests high-impact rewrites incorporating action verbs and quantifiable metrics.\n"
            "• **Match Score:** An explainable indicator of how well resume evidence covers role requirements. It is an alignment indicator, not an objective guarantee of hiring."
        )


def main() -> None:
    """Main application lifecycle controller."""
    configure_logging()
    st.set_page_config(
        page_title="Resume Analyser",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        st.error(f"Application configuration error: {exc}")
        return

    section = render_sidebar(settings)

    if section == "Dashboard":
        render_page_heading(
            title="Resume Analyser",
            eyebrow="CAREER INTELLIGENCE",
            subtitle="Optimize your resume for ATS filters and target job descriptions.",
            introduction=(
                "Gain clear insights into your resume's strengths and areas for improvement. "
                "Compare your background against any job description for structured, evidence-based feedback."
            ),
        )
        render_feature_overview()
        st.write("")
        render_workspace(settings)
    elif section == "Resume Analysis":
        render_page_heading(
            title="Resume Analysis",
            eyebrow="DETAILED REPORT",
            subtitle="Transform your resume into a competitive application.",
            introduction=(
                "Submit your resume below to generate an ATS audit, skill match breakdown, "
                "STAR bullet point rewrites, and prioritized next steps."
            ),
        )
        render_workspace(settings)
    else:
        render_about()


if __name__ == "__main__":
    main()
