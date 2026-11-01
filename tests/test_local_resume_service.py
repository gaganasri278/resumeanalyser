"""Deterministic tests for local keyword-based analysis."""

import pytest

from app.services.local_resume_service import LocalResumeAnalyzer
from app.services.resume_service import ResumeAnalysis, ResumeAnalysisError


def test_local_analysis_detects_skills_and_job_matches() -> None:
    """Known resume skills match the job description and retain evidence."""
    analyzer = LocalResumeAnalyzer(max_resume_chars=2000)

    result = analyzer.analyze(
        "Built a Python and SQL reporting service. Used clear communication.",
        "Python developer using SQL and Docker. Strong communication required.",
        job_title="Backend Engineer",
    )

    assert result.analysis_mode == "Local keyword-based"
    assert result.job_match is not None
    assert "Python" in result.job_match.matching_skills
    assert "SQL" in result.job_match.matching_skills
    assert "Communication" in result.job_match.matching_skills
    assert result.job_match.missing_skills == ["Docker"]
    assert "python" in result.job_match.matching_keywords
    assert "docker" in result.job_match.missing_keywords
    assert any("Python and SQL" in item for item in result.job_match.relevant_evidence)
    assert result.job_match.strengths
    assert (
        result.job_match.role_recommendations
        or result.job_match.improvement_suggestions
    )
    assert result.job_match.target_role == "Backend Engineer"
    assert 0 <= result.job_match.match_score <= 100
    assert "indicates keyword coverage" in result.job_match.match_score_explanation
    assert result.job_recommendations == []
    assert "Semantic summary requires Gemini mode" in result.resume_summary


def test_local_analysis_generates_ats_checks_and_action_plan() -> None:
    """Deterministic ATS checks and prioritized action plan are populated."""
    analyzer = LocalResumeAnalyzer()
    resume = (
        "Experience:\n"
        "Senior Software Engineer at TechCorp from 2020 to 2024.\n"
        "Developed Python backend services for 500,000+ users.\n"
        "Education:\n"
        "B.S. in Computer Science.\n"
        "Skills:\n"
        "Python, SQL, Docker, Git.\n"
        "Contact: dev@example.com | (555) 123-4567\n"
    )

    result = analyzer.analyze(resume)

    assert len(result.ats_formatting_checks) >= 3
    heading_check = next(
        (c for c in result.ats_formatting_checks if "Heading" in c.check_name), None
    )
    assert heading_check is not None
    assert heading_check.status == "pass"

    contact_check = next(
        (c for c in result.ats_formatting_checks if "Contact" in c.check_name), None
    )
    assert contact_check is not None
    assert contact_check.status == "pass"

    assert len(result.prioritized_action_plan) == 3
    assert result.prioritized_action_plan[0].priority == "High"


def test_local_analysis_is_deterministic_and_has_no_external_provider() -> None:
    """Repeated local runs return identical results without network access."""
    analyzer = LocalResumeAnalyzer()
    inputs = ("Python project experience", "Python developer role")

    first = analyzer.analyze(*inputs)
    second = analyzer.analyze(*inputs)

    assert first.model_dump() == second.model_dump()


def test_local_result_validates_with_resume_analysis_schema() -> None:
    """The local constructor result validates against the strict schema."""
    result = LocalResumeAnalyzer().analyze(
        "Built a Python service.",
        "Python role requiring Docker.",
    )

    validated = ResumeAnalysis.model_validate(result.model_dump())

    assert isinstance(result, ResumeAnalysis)
    assert validated == result
    assert validated.analysis_mode == "Local keyword-based"
    assert validated.job_match is not None
    assert validated.job_match.missing_skills == ["Docker"]


def test_local_analysis_without_job_description_has_no_match() -> None:
    """A general local scan does not fabricate a role comparison."""
    result = LocalResumeAnalyzer().analyze("Python and communication skills")

    assert result.job_match is None
    assert result.technical_skills == ["Python"]
    assert result.soft_skills == ["Communication"]
    assert result.analysis_mode == "Local keyword-based"


@pytest.mark.parametrize(
    ("resume_text", "job_description", "message"),
    [
        ("  ", None, "Paste or upload"),
        ("x" * 11, None, "Resume text exceeds"),
        ("resume", "x" * 11, "Job description exceeds"),
    ],
)
def test_local_analysis_rejects_invalid_inputs(
    resume_text: str,
    job_description: str | None,
    message: str,
) -> None:
    """Blank and over-limit inputs fail with safe validation errors."""
    analyzer = LocalResumeAnalyzer(max_resume_chars=10)

    with pytest.raises(ResumeAnalysisError, match=message):
        analyzer.analyze(resume_text, job_description)
