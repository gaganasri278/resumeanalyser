"""Streamlit UI workflow tests for Gemini mode, local mode, and quota fallback."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.integrations.ai_provider import GeminiResumeProvider
from app.services.resume_service import ResumeAnalysisError, ResumeService

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
GEMINI_MODE = "Google Gemini (Recommended)"
LOCAL_MODE = "Local keyword-based (Offline / Fallback)"
APP_TEST_TIMEOUT_SECONDS = 60


def test_local_mode_runs_without_gemini_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local UI workflow analyzes input without constructing a Gemini provider."""

    def reject_provider(*args: object, **kwargs: object) -> None:
        raise AssertionError("Local analysis must not construct a Gemini provider.")

    monkeypatch.setattr(GeminiResumeProvider, "__init__", reject_provider)
    app = AppTest.from_file(str(APP_PATH)).run(timeout=APP_TEST_TIMEOUT_SECONDS)

    # Explicitly select LOCAL_MODE so test runs independently of whether .env is configured
    app.selectbox[0].set_value(LOCAL_MODE).run(timeout=APP_TEST_TIMEOUT_SECONDS)
    app.text_area[0].set_value(
        "Built Python and SQL services with clear communication."
    )
    app.text_area[1].set_value("Python role requiring SQL and Docker.")
    app.get("form_submit_button")[0].click()
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)

    result = app.session_state["resume_analysis"]
    assert result.analysis_mode == "Local keyword-based"
    assert result.job_match is not None
    assert "Python" in result.job_match.matching_skills
    assert "SQL" in result.job_match.matching_skills
    assert result.job_match.missing_skills == ["Docker"]
    assert len(app.get("download_button")) == 1
    assert "PDF" in app.download_button[0].label
    assert "JSON" not in app.download_button[0].label
    assert not app.exception


def test_gemini_mode_rejects_request_without_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini mode stops submission unless user consent is explicitly checked."""

    def reject_service_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("Service must not be called when consent is not given.")

    monkeypatch.setattr(ResumeService, "analyze", reject_service_call)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-mock")

    app = AppTest.from_file(str(APP_PATH)).run(timeout=APP_TEST_TIMEOUT_SECONDS)
    app.selectbox[0].set_value(GEMINI_MODE).run(timeout=APP_TEST_TIMEOUT_SECONDS)

    app.text_area[0].set_value("Experienced Python developer.")
    assert app.checkbox[0].value is False

    app.get("form_submit_button")[0].click()
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)

    assert any("Consent is required" in error.value for error in app.error)
    assert "resume_analysis" not in app.session_state
    assert not app.exception


def test_gemini_mode_runs_with_consent_and_mocked_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini mode processes input when consent is granted."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-mock")

    fake_result_json = json.dumps(
        {
            "resume_summary": "Skilled backend engineer.",
            "technical_skills": ["Python", "Docker"],
            "soft_skills": ["Leadership"],
            "experience_assessment": "Extensive enterprise development experience.",
            "bullet_point_improvements": [],
            "ats_formatting_checks": [],
            "warnings": [],
            "prioritized_action_plan": [],
        }
    )

    class FakeGeminiProvider:
        analysis_mode = "Gemini-assisted"

        def generate(self, *args: object, **kwargs: object) -> str:
            return fake_result_json

        def test_connection(self) -> tuple[bool, str]:
            return True, "Connected"

    monkeypatch.setattr(
        "app.integrations.ai_provider.create_resume_provider",
        lambda settings: FakeGeminiProvider(),
    )

    app = AppTest.from_file(str(APP_PATH)).run(timeout=APP_TEST_TIMEOUT_SECONDS)
    app.selectbox[0].set_value(GEMINI_MODE).run(timeout=APP_TEST_TIMEOUT_SECONDS)

    app.text_area[0].set_value("Python developer with Docker skills.")
    app.checkbox[0].set_value(True)
    app.get("form_submit_button")[0].click()
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)

    result = app.session_state["resume_analysis"]
    assert result.analysis_mode == "Gemini-assisted"
    assert result.resume_summary == "Skilled backend engineer."
    assert len(app.get("download_button")) == 1
    assert "PDF" in app.download_button[0].label
    assert "JSON" not in app.download_button[0].label
    assert not app.exception


def test_gemini_quota_failure_offers_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quota or rate limit failure offers immediate local keyword fallback."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-mock")

    def fail_with_quota(*args: object, **kwargs: object) -> None:
        raise ResumeAnalysisError(
            "Gemini rate limit or quota exceeded.",
            local_fallback_available=True,
        )

    monkeypatch.setattr(ResumeService, "analyze", fail_with_quota)
    app = AppTest.from_file(str(APP_PATH)).run(timeout=APP_TEST_TIMEOUT_SECONDS)
    app.selectbox[0].set_value(GEMINI_MODE).run(timeout=APP_TEST_TIMEOUT_SECONDS)

    app.text_area[0].set_value("Python and SQL developer.")
    app.text_area[1].set_value("Seeking Python and Docker.")
    app.checkbox[0].set_value(True)
    app.get("form_submit_button")[0].click()
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)

    assert "pending_local_analysis" in app.session_state
    fallback_buttons = [
        btn
        for btn in app.get("button")
        if "Local Keyword Analysis" in btn.label or "Run Local" in btn.label
    ]
    assert len(fallback_buttons) >= 1

    fallback_buttons[0].click()
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)

    result = app.session_state["resume_analysis"]
    assert result.analysis_mode == "Local keyword-based"
    assert "pending_local_analysis" not in app.session_state
    assert not app.exception
