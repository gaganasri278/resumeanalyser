"""Unit tests for resume analysis validation and response parsing."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.config.settings import Settings
from app.integrations.ai_provider import AIProviderError
from app.services.resume_service import (
    ResumeAnalysis,
    ResumeAnalysisError,
    ResumeService,
)


class FakeProvider:
    """Fake analysis provider for isolated service tests."""

    def __init__(self, content: str = "", error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.analysis_mode = "Gemini-assisted"
        self.calls: list[tuple[str, str, str | None, str | None]] = []

    def generate(
        self,
        resume_text: str,
        request_id: str,
        job_description: str | None = None,
        job_title: str | None = None,
    ) -> str:
        """Return configured JSON response and record call metadata."""
        self.calls.append((resume_text, request_id, job_description, job_title))
        if self.error is not None:
            raise self.error
        return self.content

    def test_connection(self) -> tuple[bool, str]:
        return True, "Connected"


def make_settings() -> Settings:
    """Return settings that do not require real credentials in tests."""
    return Settings(
        gemini_api_key="",
        gemini_model="gemini-3.5-flash-lite",
        max_resume_chars=1000,
        request_timeout_seconds=1.0,
        max_output_tokens=500,
    )


def valid_payload() -> dict[str, Any]:
    """Return a valid rich analysis payload."""
    return {
        "resume_summary": "Python developer with cloud experience.",
        "technical_skills": ["Python", "Docker"],
        "soft_skills": ["Problem solving"],
        "experience_assessment": "Solid mid-level backend experience.",
        "bullet_point_improvements": [
            {
                "original_or_issue": "Built backend APIs",
                "suggested_revision": "Architected RESTful APIs with FastAPI, reducing response latency by 35%.",
                "explanation": "Adds quantification and specific framework context.",
            }
        ],
        "ats_formatting_checks": [
            {
                "check_name": "Standard Section Headings",
                "status": "pass",
                "finding": "Standard sections found.",
                "suggestion": "No change needed.",
            }
        ],
        "warnings": [],
        "prioritized_action_plan": [
            {
                "priority": "High",
                "title": "Quantify Outcomes",
                "action": "Add percentages and metrics to project bullets.",
                "impact": "Improves recruiter engagement.",
            }
        ],
        "missing_skills": [],
        "learning_suggestions": ["Explore Kubernetes deployment."],
        "resume_improvements": ["Highlight CI/CD workflows."],
    }


def test_analyze_returns_validated_result() -> None:
    """Valid model output is parsed into typed analysis data."""
    provider = FakeProvider(json.dumps(valid_payload()))
    service = ResumeService(make_settings(), provider=provider)

    result = service.analyze(
        "  Python developer with cloud experience.  ",
        request_id="test-request-1",
        job_title="Backend Engineer",
    )

    assert result.resume_summary.startswith("Python developer")
    assert result.analysis_mode == "Gemini-assisted"
    assert result.technical_skills == ["Python", "Docker"]
    assert len(result.bullet_point_improvements) == 1
    assert result.bullet_point_improvements[0].original_or_issue == "Built backend APIs"
    assert provider.calls == [
        (
            "Python developer with cloud experience.",
            "test-request-1",
            None,
            "Backend Engineer",
        )
    ]


def test_analyze_strips_markdown_code_fences() -> None:
    """Markdown code fences (```json ... ```) are safely unpacked."""
    raw = f"```json\n{json.dumps(valid_payload())}\n```"
    provider = FakeProvider(raw)
    service = ResumeService(make_settings(), provider=provider)

    result = service.analyze("Sample resume text")
    assert result.resume_summary.startswith("Python developer")


def test_resume_analysis_accepts_supported_modes() -> None:
    """Supported analysis modes are accepted."""
    gemini_result = ResumeAnalysis.model_validate(valid_payload())
    local_result = ResumeAnalysis.model_validate(
        {**valid_payload(), "analysis_mode": "Local keyword-based"}
    )

    assert gemini_result.analysis_mode == "Gemini-assisted"
    assert local_result.analysis_mode == "Local keyword-based"

    with pytest.raises(ValidationError):
        ResumeAnalysis.model_validate(
            {**valid_payload(), "analysis_mode": "UnsupportedProvider"}
        )


def test_analyze_rejects_empty_resume() -> None:
    """Blank input is rejected before calling the AI provider."""
    provider = FakeProvider("{}")
    service = ResumeService(make_settings(), provider=provider)

    with pytest.raises(ResumeAnalysisError, match="Paste or upload your resume"):
        service.analyze("  \n")
    assert provider.calls == []


def test_analyze_rejects_oversized_resume() -> None:
    """Input beyond configured limit is rejected."""
    provider = FakeProvider("{}")
    service = ResumeService(make_settings(), provider=provider)

    with pytest.raises(ResumeAnalysisError, match="configured limit"):
        service.analyze("x" * 1001)
    assert provider.calls == []


def test_analyze_rejects_invalid_ai_response() -> None:
    """Malformed provider output translates to a safe application error."""
    provider = FakeProvider("not-json-content")
    service = ResumeService(make_settings(), provider=provider)

    with pytest.raises(ResumeAnalysisError, match="could not be validated"):
        service.analyze("A resume with work experience.")


def test_analyze_translates_provider_failure_to_safe_error() -> None:
    """Provider errors become user-safe service errors without losing request IDs."""
    provider = FakeProvider(error=AIProviderError("Safe Gemini failure"))
    service = ResumeService(make_settings(), provider=provider)

    with pytest.raises(ResumeAnalysisError, match="Safe Gemini failure"):
        service.analyze("A resume with work experience.", request_id="req-42")

    assert provider.calls == [("A resume with work experience.", "req-42", None, None)]


def test_quota_error_exposes_local_fallback_signal() -> None:
    """Service preserves provider quota fallback signal for the UI."""
    provider = FakeProvider(
        error=AIProviderError(
            "Gemini quota exhausted.",
            local_fallback_available=True,
        )
    )
    service = ResumeService(make_settings(), provider=provider)

    with pytest.raises(ResumeAnalysisError) as error:
        service.analyze("A resume with work experience.")

    assert error.value.local_fallback_available


def test_service_requires_key_when_using_default_provider() -> None:
    """Missing credentials fail when constructing the default provider."""
    with pytest.raises(ResumeAnalysisError, match="API key is not configured"):
        ResumeService(make_settings())


def test_analyze_compares_resume_with_job_description() -> None:
    """A job description reaches the provider and yields validated match data."""
    payload = valid_payload()
    payload["job_match"] = {
        "target_role": "Python Cloud Engineer",
        "fit_summary": "Strong skill alignment with target requirements.",
        "match_score": 85,
        "match_score_explanation": "85% calculated based on 4 of 5 core requirements matched.",
        "matching_skills": ["Python", "Docker"],
        "missing_skills": ["Terraform"],
        "insufficiently_evidenced_skills": [],
        "job_requirements_summary": ["Python", "Docker", "Terraform"],
        "strengths": ["Demonstrated backend proficiency"],
        "experience_relevance": "Directly relevant background.",
        "project_relevance": "Strong architectural projects.",
        "role_recommendations": ["Highlight infrastructure as code."],
    }
    provider = FakeProvider(json.dumps(payload))
    service = ResumeService(make_settings(), provider=provider)

    result = service.analyze(
        "Python and Docker experience",
        job_description="Seeking Python and Terraform experience.",
        job_title="Python Cloud Engineer",
    )

    assert result.job_match is not None
    assert result.job_match.match_score == 85
    assert result.job_match.matching_skills == ["Python", "Docker"]
    assert result.job_match.missing_skills == ["Terraform"]


def test_analyze_requires_job_match_for_supplied_description() -> None:
    """Missing job_match when description was given is rejected."""
    service = ResumeService(
        make_settings(),
        provider=FakeProvider(json.dumps(valid_payload())),
    )

    with pytest.raises(ResumeAnalysisError, match="comparison could not be completed"):
        service.analyze("Python developer", job_description="Python role")


def test_analyze_rejects_overlong_job_description() -> None:
    """Oversized job descriptions are rejected before provider call."""
    provider = FakeProvider(json.dumps(valid_payload()))
    service = ResumeService(make_settings(), provider=provider)

    with pytest.raises(ResumeAnalysisError, match="Job description exceeds"):
        service.analyze("Python developer", job_description="x" * 1001)

    assert provider.calls == []
