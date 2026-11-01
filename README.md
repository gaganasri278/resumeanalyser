# Resume Analyser

A professional, modern career intelligence and ATS resume analysis platform built with Python, Streamlit, and Google Gemini.

---

## Overview

**Resume Analyser** is a production-ready application designed to help job seekers, graduates, and professionals optimize their resumes for modern Applicant Tracking Systems (ATS) and competitive job descriptions. 

By leveraging the official Google Gemini API (via the `google-genai` SDK) alongside a deterministic local keyword engine, Resume Analyser delivers evidence-based evaluations, actionable STAR-method bullet rewrites, transparent skill-match assessments, and prioritized action plans.

---

## Key Features

- **Google Gemini AI Integration:** Uses Google's official `google-genai` SDK with structured JSON schemas and default model `gemini-3.5-flash-lite` (or `gemini-3.8-flash`).
- **One-Click Connection Probe:** Test your Gemini API key safely directly from the sidebar without uploading any documents.
- **Resilient Retry & Timeout Architecture:** Built-in bounded exponential backoff handles transient network errors and server load (HTTP 429, 502, 503, 504) seamlessly.
- **Document Text Extraction:** Bounded and validated text extraction from both **PDF** and **DOCX** files (up to 5 MB), including table parsing, with clear warnings for scanned or unreadable documents.
- **Role Match & Explainable Scoring:** Transparent alignment score based on requirement coverage and skill overlap. (Clearly presented as an alignment metric, not a subjective hiring guarantee).
- **Skills Matrix:** Categorized breakdown of Matched Skills, Missing Skills, Insufficiently Evidenced Skills, Technical Skills, and Soft Skills.
- **STAR Bullet Point Rewrites:** High-impact suggestions rewriting passive responsibilities into quantified achievement statements (Action Verb + Context + Result).
- **ATS Readability & Formatting Checks:** Audits standard section headers, contact info presence, text density, and parseability.
- **Prioritized Action Plan:** High, Medium, and Low priority steps for immediate resume enhancement.
- **100% Offline Local Fallback:** Full deterministic keyword analysis available without an API key or internet access, ensuring the application remains functional even when quotas or network connections fail.
- **Privacy & Security First:** Explicit user consent required before sending any resume data to Gemini; no permanent file storage; in-memory stream processing; zero credential leaks in logs or UI.
- **Professional PDF Report Export:** Instant download of publication-ready, multi-page PDF evaluation reports powered by ReportLab, featuring navy-and-white styling, running headers, and dynamic page numbering.

---

## Screenshots

> *Add your application screenshots in a `docs/screenshots/` folder and link them here.*

```markdown
![Resume Analyser Dashboard](docs/screenshots/dashboard.png)
*Figure 1: Workspace overview with file upload, target role inputs, and analysis engine selection.*

![Role Match and ATS Report](docs/screenshots/analysis_report.png)
*Figure 2: Match score gauge, skills matrix, STAR bullet rewrites, and ATS formatting check.*
```

---

## Technologies Used

- **Language:** Python 3.12+
- **Frontend / App Framework:** [Streamlit](https://streamlit.io/) (>=1.35.0)
- **AI Engine:** Official Google GenAI Python SDK ([`google-genai`](https://pypi.org/project/google-genai/))
- **PDF Generation:** [ReportLab](https://www.reportlab.com/) (>=4.0.0)
- **Data Validation:** [Pydantic](https://docs.pydantic.dev/) v2 (>=2.7.0)
- **Document Parsers:** [`pypdf`](https://pypi.org/project/pypdf/) (>=5.0.0), [`python-docx`](https://pypi.org/project/python-docx/) (>=1.1.2)
- **Environment Management:** [`python-dotenv`](https://pypi.org/project/python-dotenv/)
- **Testing & Quality:** [`pytest`](https://docs.pytest.org/), [`ruff`](https://docs.astral.sh/ruff/)

---

## Architecture

```text
Resume_analyser/
├── app/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Environment & Streamlit secrets loader
│   ├── integrations/
│   │   ├── __init__.py
│   │   └── ai_provider.py       # Google Gemini provider adapter & connection probe
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── resume_prompt.py     # Structured system prompt & schema templates
│   ├── services/
│   │   ├── __init__.py
│   │   ├── resume_service.py    # Gemini resume analysis service & Pydantic models
│   │   ├── local_resume_service.py # Deterministic local keyword & ATS analyzer
│   │   └── pdf_report_service.py # Professional ReportLab PDF document generator
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py             # Polished CSS styles, cards, pills, & gauges
│   │   └── components.py        # Reusable UI widgets & report rendering
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging_config.py    # Safe console logging (no PII / API keys)
│   │   ├── rate_limiter.py      # Process-local rate and concurrency limiter
│   │   └── resume_parser.py     # Secure PDF/DOCX text extraction
│   └── main.py                  # Streamlit entry point
├── tests/                       # Complete automated offline test suite
├── .env.example                 # Example configuration template
├── .gitignore                   # Excludes .env, .venv, uploads, secrets
├── pyproject.toml               # pytest & ruff configuration
├── requirements.txt             # Runtime dependencies
└── requirements-dev.txt         # Development & test dependencies
```

---

## Prerequisites

- **Operating System:** Windows 10/11, macOS, or Linux
- **Python:** Version 3.12 or higher
- **Gemini API Key (Optional for Local Mode, Required for Gemini Mode):** Obtain a free API key at [Google AI Studio](https://aistudio.google.com/apikey).

---

## Installation & Setup (Windows PowerShell)

### 1. Open PowerShell and Navigate to the Project

```powershell
Set-Location "$HOME\OneDrive\Desktop\Resume_analyser"
```

### 2. Create and Activate a Virtual Environment

```powershell
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
.\.venv\Scripts\Activate.ps1
```

*(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` first).*

### 3. Install Dependencies

```powershell
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 4. Configure Your Gemini API Key

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` in a text editor (e.g. `notepad .env`) and add your Gemini API key:

```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here...
```

> **Security Note:** Never commit your `.env` file or paste API keys into code. `.env` is automatically ignored by `.gitignore`.

---

## Launching the Application

Start the Streamlit application from the project root:

```powershell
& .\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Streamlit will print the local URL in your console:
```text
Local URL: http://localhost:8501
```

Open `http://localhost:8501` in your web browser.

---

## Running the Automated Test Suite

All tests run completely **offline** using mocked SDK endpoints. No live API calls are made and no real API key is required.

Run the test suite and code quality checks:

```powershell
# Run all unit and workflow tests
& .\.venv\Scripts\python.exe -m pytest

# Run Ruff linter
& .\.venv\Scripts\python.exe -m ruff check app tests

# Run Ruff formatting verification
& .\.venv\Scripts\python.exe -m ruff format --check app tests
```

---

## Configuration Reference

The application reads settings from `.env`, system environment variables, or Streamlit secrets (`secrets.toml`):

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *Empty* | Your Google Gemini API key from Google AI Studio. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini model identifier (e.g. `gemini-3.5-flash-lite`, `gemini-3.8-flash`). |
| `MAX_RESUME_CHARS` | `30000` | Max character length for resume and job description text. |
| `GEMINI_TIMEOUT_SECONDS` | `30` | API request timeout in seconds (bounded exponential backoff on transient errors). |
| `GEMINI_MAX_OUTPUT_TOKENS` | `4096` | Maximum tokens for structured JSON generation. |
| `MAX_ANALYSES_PER_MINUTE` | `10` | Rate limiter threshold per minute. |
| `MAX_CONCURRENT_ANALYSES`| `3` | Maximum concurrent analyses per process. |

---

## Privacy and Data Security

- **Consent-Gated Processing:** Resume content is never sent to Google Gemini unless you check the explicit consent box before submitting.
- **In-Memory Handling:** Uploaded documents are read in-memory as byte buffers and discarded. No files are saved to disk or databases.
- **Local Fallback:** If you prefer not to send data externally, select **Local keyword-based mode** for 100% offline analysis.
- **No Sensitive Logging:** Resumes, contact details, and API keys are automatically redacted and excluded from log streams.

---

## Troubleshooting

| Problem | Cause | Resolution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'app'` | Running script from inside the `app/` directory. | Always run from the project root: `streamlit run app/main.py`. |
| `GEMINI_API_KEY is not configured` | Missing key in `.env` or environment. | Add `GEMINI_API_KEY=your_key` to `.env` or use Local Mode. |
| `401 / API_KEY_INVALID` | Invalid key or missing API enablement. | Verify your key at [Google AI Studio](https://aistudio.google.com/apikey). |
| `429 / RESOURCE_EXHAUSTED` | Free tier quota or rate limit exceeded. | Wait a moment before retrying, or click the **Run Local Keyword Analysis Instead** button. |
| `503 / 504 / DEADLINE_EXCEEDED` | Google Gemini model high demand or server timeout. | Automatic retry handles temporary surges. For higher stability, use `gemini-3.5-flash-lite` in `.env` or use Local Mode. |
| `No selectable text was found` | Scanned or image-only PDF document. | Upload a text-based PDF/DOCX or copy and paste the plain text directly. |
| `Port 8501 is already in use` | Another instance of Streamlit is running. | Run with `--server.port 8502` or terminate existing python processes. |

---

## Git & GitHub Publishing Instructions

To publish this project to your GitHub repository named `resumeanalyser`, follow these exact steps:

### 1. Verify Git Installation

In PowerShell, verify Git is installed:
```powershell
git --version
```
*(If Git is not installed, install Git for Windows from [git-scm.com](https://git-scm.com) or run `winget install --id Git.Git -e` in an Administrator terminal).*

### 2. Initialize Git Repository (From Project Root)

```powershell
Set-Location "$HOME\OneDrive\Desktop\Resume_analyser"

# Initialize repository
git init

# Configure branch name
git branch -M main
```

### 3. Verify .gitignore Exclusions

Before staging, verify that private files (`.env`, `.venv`, upload caches) are excluded:
```powershell
git status
```
*(Confirm `.env` and `.venv/` do NOT appear in Untracked files).*

### 4. Stage and Commit Files

```powershell
git add .
git commit -m "feat: upgrade Resume Analyser with Google Gemini, ATS audit, and professional UI"
```

### 5. Link and Push to Your GitHub Repository

Create a new repository named `resumeanalyser` on your GitHub account, then run:

```powershell
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/resumeanalyser.git
git push -u origin main
```

---

## License

This project is licensed under the [MIT License](LICENSE).
