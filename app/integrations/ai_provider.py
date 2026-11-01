"""Official Google Gemini API provider adapter with resilient error handling and bounded retries."""

import logging
import re
import time
from typing import Any, Literal, Protocol

import httpx
from google import genai
from google.genai import errors, types

from app.config.settings import Settings
from app.prompts.resume_prompt import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# Pattern to detect and redact API keys if they ever appear in strings or error messages
_API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z-_]{35}")

# HTTP status codes that represent transient failures suitable for bounded retry
_TRANSIENT_STATUS_CODES = {429, 502, 503, 504}


def sanitize_log_message(msg: Any) -> str:
    """Strip potential API keys from string representations."""
    return _API_KEY_PATTERN.sub("[REDACTED_API_KEY]", str(msg))


class AIProviderError(Exception):
    """Expected provider or provider-configuration failure."""

    def __init__(self, message: str, *, local_fallback_available: bool = False) -> None:
        super().__init__(message)
        self.local_fallback_available = local_fallback_available


class ResumeAnalysisProvider(Protocol):
    """Contract for providers that return structured resume analysis JSON."""

    analysis_mode: Literal["Gemini-assisted", "Local keyword-based"]

    def generate(
        self,
        resume_text: str,
        request_id: str,
        job_description: str | None = None,
        job_title: str | None = None,
    ) -> str:
        """Generate analysis JSON for the supplied resume text."""
        ...

    def test_connection(self) -> tuple[bool, str]:
        """Test API connectivity with a minimal harmless probe."""
        ...


class GeminiResumeProvider:
    """Google Gemini adapter using the official google-genai SDK with exponential backoff."""

    analysis_mode: Literal["Gemini-assisted"] = "Gemini-assisted"

    def __init__(
        self,
        settings: Settings,
        model: str | None = None,
        client: genai.Client | None = None,
        max_retries: int = 2,
        initial_backoff_seconds: float = 1.0,
    ) -> None:
        """Configure the Gemini client, allowing an injected test client."""
        api_key = settings.gemini_api_key.strip()
        if client is None and not api_key:
            raise AIProviderError(
                "Google Gemini API key is not configured. "
                "Set GEMINI_API_KEY in your .env file, environment variables, or Streamlit secrets."
            )

        self._settings = settings
        raw_model = (model or settings.gemini_model).strip()
        # Normalize model identifier if prefixed with models/
        self._model = (
            raw_model
            if not raw_model.startswith("models/")
            else raw_model[len("models/") :]
        )
        self._provider_name = "Google Gemini"
        self._max_retries = max(0, max_retries)
        self._initial_backoff = max(0.1, initial_backoff_seconds)

        if client is not None:
            self._client = client
        else:
            timeout_ms = int(settings.request_timeout_seconds * 1000)
            http_options = types.HttpOptions(timeout=timeout_ms)
            self._client = genai.Client(api_key=api_key, http_options=http_options)

    @property
    def model_name(self) -> str:
        """Return the active Gemini model name."""
        return self._model

    def test_connection(self) -> tuple[bool, str]:
        """Verify the Gemini connection with a minimal probe without sending resume data."""
        try:
            config = types.GenerateContentConfig(
                max_output_tokens=5,
                temperature=0.0,
                http_options=types.HttpOptions(timeout=10000),
            )
            # Fast probe with zero retries to keep UI responsive
            response = self._execute_with_retry(
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents="Ping",
                    config=config,
                ),
                operation_name="Connection probe",
                request_id="probe",
                max_retries=0,
            )
            if response and getattr(response, "text", None):
                return (
                    True,
                    f"Successfully connected to Google Gemini ({self._model}). API is responding.",
                )
            return True, f"Connection verified with Google Gemini ({self._model})."
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code in {400, 401, 403}:
                return (
                    False,
                    "Gemini API key was rejected or lacks permissions. "
                    "Check your key at https://aistudio.google.com/apikey",
                )
            if code == 404:
                return (
                    False,
                    f"Model '{self._model}' was not found (404). "
                    "Note: Google retired gemini-2.5-flash. Recommended: gemini-3.5-flash-lite or gemini-3.8-flash.",
                )
            if code in {503, 504}:
                return (
                    False,
                    f"Connected to Gemini API, but '{self._model}' returned {code} (High Demand / Timeout). "
                    "Consider setting GEMINI_MODEL=gemini-3.5-flash-lite in your .env for high stability.",
                )
            if code == 429:
                return (
                    False,
                    "Gemini rate limit or quota exceeded. Review usage limits at Google AI Studio.",
                )
            return (
                False,
                f"Gemini probe returned error code {code}. Please verify settings.",
            )
        except Exception as exc:
            safe_msg = sanitize_log_message(str(exc))
            logger.warning("Gemini probe failed: %s", safe_msg)
            if "RemoteProtocolError" in safe_msg or "disconnected" in safe_msg:
                return (
                    False,
                    "Server disconnected without sending a response. Check network connectivity or retry.",
                )
            return (
                False,
                "Could not connect to Google Gemini. Check your network or API key.",
            )

    def _execute_with_retry(
        self,
        call_fn: Any,
        operation_name: str,
        request_id: str,
        max_retries: int | None = None,
    ) -> Any:
        """Execute a Gemini SDK call with bounded exponential backoff for transient failures."""
        retries = self._max_retries if max_retries is None else max_retries
        backoff = self._initial_backoff

        for attempt in range(retries + 1):
            try:
                return call_fn()
            except errors.APIError as exc:
                code = getattr(exc, "code", None)

                # Non-transient errors must NOT be retried
                if code in {400, 401, 403, 404}:
                    raise

                # Transient errors: retry with backoff if attempts remain
                if code in _TRANSIENT_STATUS_CODES and attempt < retries:
                    logger.warning(
                        "%s transient error (code=%s); retrying %d/%d after %.1fs; request_id=%s",
                        operation_name,
                        code,
                        attempt + 1,
                        retries,
                        backoff,
                        request_id,
                    )
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue

                # Out of retries or non-retryable
                raise

            except (httpx.TimeoutException, TimeoutError):
                if attempt < retries:
                    logger.warning(
                        "%s timed out; retrying %d/%d after %.1fs; request_id=%s",
                        operation_name,
                        attempt + 1,
                        retries,
                        backoff,
                        request_id,
                    )
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise

            except (
                httpx.RemoteProtocolError,
                httpx.NetworkError,
                ConnectionError,
            ) as exc:
                if attempt < retries:
                    logger.warning(
                        "%s network/protocol interruption (%s); retrying %d/%d; request_id=%s",
                        operation_name,
                        type(exc).__name__,
                        attempt + 1,
                        retries,
                        request_id,
                    )
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise

    def generate(
        self,
        resume_text: str,
        request_id: str,
        job_description: str | None = None,
        job_title: str | None = None,
    ) -> str:
        """Request structured JSON resume analysis from Gemini with resilience safeguards."""
        prompt = build_user_prompt(
            resume_text=resume_text,
            job_description=job_description,
            job_title=job_title,
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            max_output_tokens=self._settings.max_output_tokens,
            temperature=0.2,
        )

        try:
            response = self._execute_with_retry(
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                ),
                operation_name="Resume analysis",
                request_id=request_id,
            )
            content = getattr(response, "text", None)

        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            raw_msg = sanitize_log_message(str(exc))
            logger.warning(
                "Gemini API error; code=%s request_id=%s detail=%s",
                code,
                request_id,
                raw_msg[:120],
            )

            if code in {400, 401, 403}:
                raise AIProviderError(
                    "Google Gemini rejected the API key or request. Please verify that "
                    "GEMINI_API_KEY is valid and the Gemini API is enabled at Google AI Studio."
                ) from None

            if code == 404:
                raise AIProviderError(
                    f"The configured Gemini model '{self._model}' was not found or is unavailable (404). "
                    "Note: Google retired gemini-2.5-flash. Please set GEMINI_MODEL=gemini-3.5-flash-lite "
                    "or gemini-3.8-flash in your .env file."
                ) from None

            if code == 429 or "RESOURCE_EXHAUSTED" in raw_msg.upper():
                raise AIProviderError(
                    "Google Gemini API quota or rate limit exceeded. "
                    "Please wait a moment before retrying, or review your project quota in Google AI Studio.",
                    local_fallback_available=True,
                ) from None

            if (
                code in {503, 504}
                or "DEADLINE_EXCEEDED" in raw_msg.upper()
                or "UNAVAILABLE" in raw_msg.upper()
            ):
                raise AIProviderError(
                    f"Google Gemini model '{self._model}' is currently experiencing high demand or timed out ({code}). "
                    "Try switching GEMINI_MODEL=gemini-3.5-flash-lite in .env for faster responses, "
                    "or run Local Analysis instead.",
                    local_fallback_available=True,
                ) from None

            raise AIProviderError(
                f"Google Gemini service returned an unexpected error ({code}). Please try again shortly.",
                local_fallback_available=True,
            ) from None

        except (httpx.TimeoutException, TimeoutError):
            logger.warning("Gemini request timed out; request_id=%s", request_id)
            raise AIProviderError(
                f"Google Gemini request timed out after {int(self._settings.request_timeout_seconds)} seconds. "
                "The server took too long to complete the request. "
                "Consider switching to gemini-3.5-flash-lite or running Local Analysis.",
                local_fallback_available=True,
            ) from None

        except (httpx.RemoteProtocolError, httpx.NetworkError, ConnectionError) as exc:
            safe_type = type(exc).__name__
            logger.warning(
                "Network connection failure to Gemini (%s); request_id=%s",
                safe_type,
                request_id,
            )
            raise AIProviderError(
                "Could not maintain a stable connection to Google Gemini (server disconnected). "
                "Check your internet connection and try again.",
                local_fallback_available=True,
            ) from None

        except Exception as exc:
            safe_type = type(exc).__name__
            logger.warning(
                "Unexpected provider exception; request_id=%s type=%s",
                request_id,
                safe_type,
            )
            raise AIProviderError(
                "Resume analysis with Gemini encountered an unexpected issue. Please try again.",
                local_fallback_available=True,
            ) from None

        if not content or not content.strip():
            logger.warning(
                "Gemini returned empty response text; request_id=%s", request_id
            )
            raise AIProviderError(
                "Google Gemini returned an empty response. Please try again.",
                local_fallback_available=True,
            )

        return content.strip()


def create_resume_provider(
    settings: Settings,
    model: str | None = None,
    client: genai.Client | None = None,
) -> ResumeAnalysisProvider:
    """Construct the resilient Google Gemini resume analysis provider."""
    return GeminiResumeProvider(settings, model=model, client=client)
