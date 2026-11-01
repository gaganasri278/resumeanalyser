"""Offline unit and integration tests for the Google Gemini provider adapter."""

from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from google import genai
from google.genai import errors

from app.config.settings import Settings
from app.integrations.ai_provider import (
    AIProviderError,
    GeminiResumeProvider,
    sanitize_log_message,
)


class FakeModelsEndpoint:
    """Fake SDK endpoint for client.models.generate_content with call tracking."""

    def __init__(
        self,
        text: str | None = None,
        error: Exception | None = None,
        errors_sequence: list[Exception] | None = None,
    ) -> None:
        self.text = text
        self.error = error
        self.errors_sequence = list(errors_sequence) if errors_sequence else []
        self.call_count = 0
        self.request_kwargs: dict[str, Any] | None = None

    def generate_content(self, **kwargs: Any) -> SimpleNamespace:
        self.call_count += 1
        self.request_kwargs = kwargs

        if self.errors_sequence:
            err = self.errors_sequence.pop(0)
            if err is not None:
                raise err
            return SimpleNamespace(text=self.text)

        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


class FakeGeminiClient:
    """Minimal fake matching the google-genai Client structure."""

    def __init__(
        self,
        text: str | None = None,
        error: Exception | None = None,
        errors_sequence: list[Exception] | None = None,
    ) -> None:
        self.models = FakeModelsEndpoint(
            text=text,
            error=error,
            errors_sequence=errors_sequence,
        )


def make_settings(
    api_key: str = "test-api-key", model: str = "gemini-3.5-flash-lite"
) -> Settings:
    """Create test settings with safe test values."""
    return Settings(
        gemini_api_key=api_key,
        gemini_model=model,
        max_resume_chars=1000,
        request_timeout_seconds=5.0,
        max_output_tokens=500,
    )


def test_provider_requires_api_key_when_no_client_injected() -> None:
    """Missing API key raises clear AIProviderError before any network attempt."""
    settings = make_settings(api_key="")
    with pytest.raises(
        AIProviderError, match="Google Gemini API key is not configured"
    ):
        GeminiResumeProvider(settings)


def test_provider_normalizes_model_prefix() -> None:
    """Model identifiers starting with models/ have the prefix stripped cleanly."""
    settings = make_settings(model="models/gemini-3.8-flash")
    provider = GeminiResumeProvider(
        settings, client=cast(genai.Client, FakeGeminiClient())
    )
    assert provider.model_name == "gemini-3.8-flash"


def test_provider_generates_content_with_expected_prompt_and_model() -> None:
    """Provider sends target model, structured prompt, and json_mime_type."""
    fake_client = FakeGeminiClient(text='{"resume_summary": "Test summary"}')
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
    )

    result = provider.generate(
        resume_text="Senior Python Engineer with 6 years experience.",
        request_id="req-123",
        job_description="Seeking Python and cloud experience.",
        job_title="Lead Developer",
    )

    assert result == '{"resume_summary": "Test summary"}'
    assert fake_client.models.request_kwargs is not None
    kwargs = fake_client.models.request_kwargs
    assert kwargs["model"] == "gemini-3.5-flash-lite"
    assert "Senior Python Engineer" in kwargs["contents"]
    assert "Lead Developer" in kwargs["contents"]
    assert "Seeking Python and cloud experience" in kwargs["contents"]
    assert kwargs["config"].response_mime_type == "application/json"


@pytest.mark.parametrize("empty_val", [None, "", "   "])
def test_provider_rejects_empty_response(empty_val: str | None) -> None:
    """Empty or whitespace response raises an actionable error."""
    fake_client = FakeGeminiClient(text=empty_val)
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=0,
    )

    with pytest.raises(AIProviderError, match="empty response"):
        provider.generate("Resume content", "req-empty")


def test_provider_handles_auth_error_without_retrying() -> None:
    """APIError 401/403 maps to clear API key guidance and is not retried."""
    auth_err = errors.APIError(
        code=401,
        response_json={
            "error": {"message": "API_KEY_INVALID", "status": "INVALID_ARGUMENT"}
        },
    )
    fake_client = FakeGeminiClient(error=auth_err)
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=2,
    )

    with pytest.raises(AIProviderError, match="rejected the API key"):
        provider.generate("Resume text", "req-auth")

    # Non-transient errors must not be retried
    assert fake_client.models.call_count == 1


def test_provider_retries_transient_503_and_succeeds() -> None:
    """Transient 503 error is retried and succeeds on subsequent attempt."""
    err_503 = errors.APIError(
        code=503,
        response_json={"error": {"message": "High demand", "status": "UNAVAILABLE"}},
    )
    fake_client = FakeGeminiClient(
        text='{"resume_summary": "Recovered summary"}',
        errors_sequence=[err_503, None],  # Fail once, then succeed
    )
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=2,
        initial_backoff_seconds=0.01,
    )

    result = provider.generate("Resume body", "req-retry")
    assert result == '{"resume_summary": "Recovered summary"}'
    assert fake_client.models.call_count == 2


def test_provider_handles_rate_limit_with_fallback_flag(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rate limit 429 sets local_fallback_available=True and logs safely."""
    rate_err = errors.APIError(
        code=429,
        response_json={
            "error": {"message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}
        },
    )
    fake_client = FakeGeminiClient(error=rate_err)
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=0,
    )

    with pytest.raises(
        AIProviderError, match="quota or rate limit exceeded"
    ) as exc_info:
        provider.generate("Confidential resume body", "req-quota")

    assert exc_info.value.local_fallback_available
    assert "Confidential resume body" not in caplog.text


def test_provider_handles_504_deadline_exceeded() -> None:
    """504 Gateway Timeout / Deadline Exceeded offers local fallback."""
    err_504 = errors.APIError(
        code=504,
        response_json={
            "error": {"message": "Deadline expired", "status": "DEADLINE_EXCEEDED"}
        },
    )
    fake_client = FakeGeminiClient(error=err_504)
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=0,
    )

    with pytest.raises(AIProviderError, match="high demand or timed out") as exc_info:
        provider.generate("Resume text", "req-504")

    assert exc_info.value.local_fallback_available


def test_provider_handles_remote_protocol_error() -> None:
    """RemoteProtocolError maps to safe connection interruption error."""
    fake_client = FakeGeminiClient(
        error=httpx.RemoteProtocolError(
            "Server disconnected without sending a response"
        )
    )
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=0,
    )

    with pytest.raises(AIProviderError, match="server disconnected") as exc_info:
        provider.generate("Resume text", "req-proto")

    assert exc_info.value.local_fallback_available


def test_provider_handles_timeout_exception() -> None:
    """httpx.TimeoutException maps to friendly timeout error."""
    fake_client = FakeGeminiClient(
        error=httpx.ReadTimeout("The read operation timed out")
    )
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=0,
    )

    with pytest.raises(AIProviderError, match="timed out") as exc_info:
        provider.generate("Resume text", "req-timeout")

    assert exc_info.value.local_fallback_available


def test_provider_handles_model_not_found() -> None:
    """404 Not Found provides clear model name diagnostic."""
    not_found = errors.APIError(
        code=404,
        response_json={"error": {"message": "Model not found", "status": "NOT_FOUND"}},
    )
    fake_client = FakeGeminiClient(error=not_found)
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
        max_retries=0,
    )

    with pytest.raises(AIProviderError, match="was not found or is unavailable"):
        provider.generate("Resume text", "req-404")


def test_connection_probe_success() -> None:
    """test_connection returns True and friendly status when probe succeeds."""
    fake_client = FakeGeminiClient(text="Pong")
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
    )

    ok, msg = provider.test_connection()
    assert ok is True
    assert "Successfully connected" in msg or "Connection verified" in msg


def test_connection_probe_failure_on_invalid_key() -> None:
    """test_connection returns False and friendly message on 401 error."""
    auth_err = errors.APIError(
        code=401,
        response_json={"error": {"message": "API_KEY_INVALID"}},
    )
    fake_client = FakeGeminiClient(error=auth_err)
    provider = GeminiResumeProvider(
        make_settings(),
        client=cast(genai.Client, fake_client),
    )

    ok, msg = provider.test_connection()
    assert ok is False
    assert "rejected" in msg or "permissions" in msg


def test_connection_probe_failure_on_503_high_demand() -> None:
    """test_connection returns False with helpful model recommendation on 503."""
    err_503 = errors.APIError(
        code=503,
        response_json={"error": {"message": "Unavailable"}},
    )
    fake_client = FakeGeminiClient(error=err_503)
    provider = GeminiResumeProvider(
        make_settings(model="gemini-3.8-flash"),
        client=cast(genai.Client, fake_client),
    )

    ok, msg = provider.test_connection()
    assert ok is False
    assert "High Demand" in msg
    assert "gemini-3.5-flash-lite" in msg


def test_sanitize_log_message_redacts_api_keys() -> None:
    """Helper redacts Gemini API key strings from output."""
    sample_key = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"
    raw = f"Error connecting with key {sample_key} on endpoint"
    sanitized = sanitize_log_message(raw)
    assert sample_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
