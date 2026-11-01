"""Environment-based application settings."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values, load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

logger = logging.getLogger(__name__)

# Primary recommended models verified against Google Gemini API (2026)
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
SUPPORTED_GEMINI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
)


def get_project_root() -> Path:
    """Resolve the absolute root directory of the Resume Analyser project."""
    return Path(__file__).resolve().parents[2]


def find_env_file() -> Path | None:
    """Locate the project .env file regardless of current working directory."""
    candidates = [
        get_project_root() / ".env",
        Path.cwd() / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_streamlit_secret(name: str) -> str:
    """Read a Streamlit secret when configured, otherwise return an empty value."""
    try:
        value = st.secrets.get(name, "")
    except (StreamlitSecretNotFoundError, FileNotFoundError, AttributeError):
        return ""
    return str(value).strip()


@dataclass(frozen=True)
class Settings:
    """Immutable configuration loaded from environment variables and secrets."""

    gemini_api_key: str
    gemini_model: str = DEFAULT_GEMINI_MODEL
    max_resume_chars: int = 30000
    request_timeout_seconds: float = 30.0
    max_output_tokens: int = 4096
    max_analyses_per_minute: int = 10
    max_concurrent_analyses: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        """Load and validate settings from environment variables and root .env file.

        Always forces re-reading of the root .env file so that changes made while
        the application is running (e.g., adding an API key) are immediately recognized.
        """
        env_file = find_env_file()
        file_values: dict[str, str | None] = {}
        if env_file:
            # Load with override=True so changes in .env take immediate effect
            load_dotenv(dotenv_path=env_file, override=True)
            try:
                file_values = dotenv_values(env_file)
            except Exception:
                file_values = {}
        else:
            load_dotenv(override=True)

        try:
            max_resume_chars = int(
                os.getenv("MAX_RESUME_CHARS")
                or file_values.get("MAX_RESUME_CHARS")
                or "30000"
            )
            timeout = float(
                os.getenv("GEMINI_TIMEOUT_SECONDS")
                or file_values.get("GEMINI_TIMEOUT_SECONDS")
                or os.getenv("REQUEST_TIMEOUT_SECONDS")
                or file_values.get("REQUEST_TIMEOUT_SECONDS")
                or "30"
            )
            max_output_tokens = int(
                os.getenv("GEMINI_MAX_OUTPUT_TOKENS")
                or file_values.get("GEMINI_MAX_OUTPUT_TOKENS")
                or os.getenv("MAX_OUTPUT_TOKENS")
                or file_values.get("MAX_OUTPUT_TOKENS")
                or "4096"
            )
            max_analyses_per_minute = int(
                os.getenv("MAX_ANALYSES_PER_MINUTE")
                or file_values.get("MAX_ANALYSES_PER_MINUTE")
                or "10"
            )
            max_concurrent_analyses = int(
                os.getenv("MAX_CONCURRENT_ANALYSES")
                or file_values.get("MAX_CONCURRENT_ANALYSES")
                or "3"
            )
        except ValueError as exc:
            raise ValueError(
                "Resume limit, timeout, and token settings must be numeric."
            ) from exc

        if max_resume_chars < 100:
            raise ValueError("MAX_RESUME_CHARS must be at least 100.")
        if timeout <= 0:
            raise ValueError("Timeout seconds must be greater than zero.")
        if max_output_tokens < 1:
            raise ValueError("Max output tokens must be greater than zero.")
        if max_analyses_per_minute < 1:
            raise ValueError("MAX_ANALYSES_PER_MINUTE must be greater than zero.")
        if max_concurrent_analyses < 1:
            raise ValueError("MAX_CONCURRENT_ANALYSES must be greater than zero.")

        # Determine Gemini model
        model_env = os.getenv("GEMINI_MODEL")
        if model_env is not None and not model_env.strip():
            raise ValueError("GEMINI_MODEL must not be empty.")
        file_model = file_values.get("GEMINI_MODEL")
        if file_model is not None and not file_model.strip():
            raise ValueError("GEMINI_MODEL must not be empty.")

        gemini_model = (
            (model_env.strip() if model_env else "")
            or (file_model.strip() if file_model else "")
            or DEFAULT_GEMINI_MODEL
        )

        # Determine Gemini API key safely without exposing or logging it
        gemini_api_key = (
            os.getenv("GEMINI_API_KEY") or file_values.get("GEMINI_API_KEY") or ""
        ).strip()

        if not gemini_api_key:
            gemini_api_key = _read_streamlit_secret("GEMINI_API_KEY")

        return cls(
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            max_resume_chars=max_resume_chars,
            request_timeout_seconds=timeout,
            max_output_tokens=max_output_tokens,
            max_analyses_per_minute=max_analyses_per_minute,
            max_concurrent_analyses=max_concurrent_analyses,
        )
