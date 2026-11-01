"""Resume analysis workflow and validated response models."""

import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config.settings import Settings
from app.integrations.ai_provider import (
    AIProviderError,
    GeminiResumeProvider,
    ResumeAnalysisProvider,
)

logger = logging.getLogger(__name__)


class BulletPointImprovement(BaseModel):
    """Specific suggestion for strengthening resume bullet points with quantifiable impact."""

    model_config = ConfigDict(extra="ignore")

    original_or_issue: str
    suggested_revision: str
    explanation: str


class ATSCheckItem(BaseModel):
    """An individual ATS compliance and formatting audit item."""

    model_config = ConfigDict(extra="ignore")

    check_name: str
    status: Literal["pass", "warning", "fail"]
    finding: str
    suggestion: str


class ActionItem(BaseModel):
    """A prioritized, actionable step to improve candidate positioning."""

    model_config = ConfigDict(extra="ignore")

    priority: Literal["High", "Medium", "Low"]
    title: str
    action: str
    impact: str


class JobMatch(BaseModel):
    """Qualitative and explainable comparison of resume evidence to a target role."""

    model_config = ConfigDict(extra="ignore")

    target_role: str = ""
    fit_summary: str = ""
    match_score: int = Field(default=0, ge=0, le=100)
    match_score_explanation: str = ""
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    insufficiently_evidenced_skills: list[str] = Field(default_factory=list)
    job_requirements_summary: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    experience_relevance: str = ""
    project_relevance: str = ""
    role_recommendations: list[str] = Field(default_factory=list)
    # Compatibility fields for legacy views
    improvement_suggestions: list[str] = Field(default_factory=list)
    matching_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    relevant_evidence: list[str] = Field(default_factory=list)


class JobRecommendation(BaseModel):
    """A potential career direction and rationale."""

    model_config = ConfigDict(extra="ignore")

    job_title: str
    rationale: str
    relevant_skills: list[str] = Field(default_factory=list)


class ResumeAnalysis(BaseModel):
    """Complete structured resume analysis returned to the user."""

    model_config = ConfigDict(extra="ignore")

    analysis_mode: Literal[
        "Gemini-assisted",
        "Local keyword-based",
    ] = "Gemini-assisted"
    resume_summary: str = ""
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    experience_assessment: str = ""
    job_match: JobMatch | None = None
    bullet_point_improvements: list[BulletPointImprovement] = Field(
        default_factory=list
    )
    ats_formatting_checks: list[ATSCheckItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    prioritized_action_plan: list[ActionItem] = Field(default_factory=list)
    # Supporting compatibility fields
    job_recommendations: list[JobRecommendation] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    learning_suggestions: list[str] = Field(default_factory=list)
    resume_improvements: list[str] = Field(default_factory=list)


class ResumeAnalysisError(Exception):
    """Expected, user-safe failure during resume analysis."""

    def __init__(self, message: str, *, local_fallback_available: bool = False) -> None:
        super().__init__(message)
        self.local_fallback_available = local_fallback_available


def _extract_json_block(text: str) -> str:
    """Extract valid JSON substring if wrapped in markdown code blocks."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    return cleaned


class ResumeService:
    """Validate input and coordinate Gemini resume analysis."""

    def __init__(
        self,
        settings: Settings,
        provider: ResumeAnalysisProvider | None = None,
    ) -> None:
        """Create the service with an injected or default Gemini provider."""
        self._settings = settings
        try:
            self._provider = provider or GeminiResumeProvider(settings)
        except AIProviderError as exc:
            raise ResumeAnalysisError(str(exc)) from None

    def analyze(
        self,
        resume_text: str,
        request_id: str = "untracked",
        job_description: str | None = None,
        job_title: str | None = None,
    ) -> ResumeAnalysis:
        """Analyze resume text, comparing it with a job description when provided."""
        cleaned_resume = resume_text.strip()
        if not cleaned_resume:
            raise ResumeAnalysisError(
                "Paste or upload your resume text before submitting."
            )

        if len(cleaned_resume) > self._settings.max_resume_chars:
            raise ResumeAnalysisError(
                f"Resume text exceeds the configured limit of {self._settings.max_resume_chars:,} characters."
            )

        cleaned_job_desc = job_description.strip() if job_description else None
        if cleaned_job_desc and len(cleaned_job_desc) > self._settings.max_resume_chars:
            raise ResumeAnalysisError(
                f"Job description exceeds the configured limit of {self._settings.max_resume_chars:,} characters."
            )

        cleaned_job_title = job_title.strip() if job_title else None

        try:
            raw_content = self._provider.generate(
                cleaned_resume,
                request_id,
                job_description=cleaned_job_desc,
                job_title=cleaned_job_title,
            )
            json_str = _extract_json_block(raw_content)
            payload = json.loads(json_str)

            if isinstance(payload, dict):
                payload["analysis_mode"] = getattr(
                    self._provider,
                    "analysis_mode",
                    "Gemini-assisted",
                )
                # Sync compatibility lists if needed
                if "job_match" in payload and payload["job_match"]:
                    match_data = payload["job_match"]
                    if not match_data.get("improvement_suggestions") and match_data.get(
                        "role_recommendations"
                    ):
                        match_data["improvement_suggestions"] = match_data[
                            "role_recommendations"
                        ]

            result = ResumeAnalysis.model_validate(payload)
            if cleaned_job_desc and result.job_match is None:
                logger.warning(
                    "Gemini returned null job_match despite job description; request_id=%s",
                    request_id,
                )
                raise ResumeAnalysisError(
                    "A job comparison could not be completed from the response. Please try again."
                )
            return result

        except AIProviderError as exc:
            logger.warning("Resume analysis provider error; request_id=%s", request_id)
            raise ResumeAnalysisError(
                str(exc),
                local_fallback_available=exc.local_fallback_available,
            ) from None
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            logger.warning(
                "Invalid AI analysis response; request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            raise ResumeAnalysisError(
                "The analysis response could not be validated. Please try again."
            ) from None
