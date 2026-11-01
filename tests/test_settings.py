"""Unit and validation tests for environment-based settings."""

from dataclasses import FrozenInstanceError

import pytest

from app.config.settings import Settings

ENVIRONMENT_KEYS = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "MAX_RESUME_CHARS",
    "GEMINI_TIMEOUT_SECONDS",
    "GEMINI_MAX_OUTPUT_TOKENS",
    "REQUEST_TIMEOUT_SECONDS",
    "MAX_OUTPUT_TOKENS",
    "MAX_ANALYSES_PER_MINUTE",
    "MAX_CONCURRENT_ANALYSES",
)


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent user environment and local .env values from affecting tests."""
    monkeypatch.setattr("app.config.settings.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.config.settings.find_env_file", lambda: None)
    for key in ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_from_env_uses_defaults_without_api_key(clean_environment: None) -> None:
    """Defaults are deterministic and configuration does not require credentials."""
    settings = Settings.from_env()

    assert settings.gemini_api_key == ""
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.max_resume_chars == 30000
    assert settings.request_timeout_seconds == 30.0
    assert settings.max_output_tokens == 4096
    assert settings.max_analyses_per_minute == 10
    assert settings.max_concurrent_analyses == 3


def test_from_env_reads_and_strips_environment_values(
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment settings are parsed and surrounding whitespace is removed."""
    monkeypatch.setenv("GEMINI_API_KEY", " test-only-gemini-key ")
    monkeypatch.setenv("GEMINI_MODEL", " gemini-2.0-flash ")
    monkeypatch.setenv("MAX_RESUME_CHARS", "4000")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "20.5")
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "800")
    monkeypatch.setenv("MAX_ANALYSES_PER_MINUTE", "7")
    monkeypatch.setenv("MAX_CONCURRENT_ANALYSES", "2")

    settings = Settings.from_env()

    assert settings.gemini_api_key == "test-only-gemini-key"
    assert settings.gemini_model == "gemini-2.0-flash"
    assert settings.max_resume_chars == 4000
    assert settings.request_timeout_seconds == 20.5
    assert settings.max_output_tokens == 800
    assert settings.max_analyses_per_minute == 7
    assert settings.max_concurrent_analyses == 2


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("MAX_RESUME_CHARS", "many"),
        ("GEMINI_TIMEOUT_SECONDS", "slow"),
        ("GEMINI_MAX_OUTPUT_TOKENS", "lots"),
        ("MAX_ANALYSES_PER_MINUTE", "often"),
        ("MAX_CONCURRENT_ANALYSES", "many"),
    ],
)
def test_from_env_rejects_non_numeric_values(
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: str,
) -> None:
    """Non-numeric limits fail validation with a consistent safe error."""
    monkeypatch.setenv(key, value)

    with pytest.raises(ValueError, match="must be numeric"):
        Settings.from_env()


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("MAX_RESUME_CHARS", "99", "at least 100"),
        ("GEMINI_TIMEOUT_SECONDS", "0", "greater than zero"),
        ("GEMINI_TIMEOUT_SECONDS", "-1", "greater than zero"),
        ("GEMINI_MAX_OUTPUT_TOKENS", "0", "greater than zero"),
        ("MAX_ANALYSES_PER_MINUTE", "0", "greater than zero"),
        ("MAX_CONCURRENT_ANALYSES", "0", "greater than zero"),
    ],
)
def test_from_env_rejects_out_of_range_values(
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: str,
    message: str,
) -> None:
    """Numeric settings outside their supported bounds are rejected."""
    monkeypatch.setenv(key, value)

    with pytest.raises(ValueError, match=message):
        Settings.from_env()


def test_from_env_rejects_blank_model(
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A whitespace-only model name is rejected."""
    monkeypatch.setenv("GEMINI_MODEL", "   ")

    with pytest.raises(ValueError, match="GEMINI_MODEL must not be empty"):
        Settings.from_env()


def test_settings_are_immutable(clean_environment: None) -> None:
    """Loaded settings cannot be mutated after construction."""
    settings = Settings.from_env()

    with pytest.raises(FrozenInstanceError):
        settings.gemini_model = "changed"  # type: ignore[misc]


def test_streamlit_secret_is_used_when_environment_key_is_absent(
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini key can be supplied through Streamlit secrets in cloud deployment."""
    monkeypatch.setattr(
        "app.config.settings.st.secrets",
        {"GEMINI_API_KEY": "test-secret-key"},
    )

    settings = Settings.from_env()

    assert settings.gemini_api_key == "test-secret-key"
