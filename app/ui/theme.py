"""Professional, polished CSS theme for Resume Analyser."""

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --ra-primary: #1E3A8A;
    --ra-primary-hover: #1D4ED8;
    --ra-accent: #2563EB;
    --ra-accent-light: #EFF6FF;
    --ra-slate-900: #0F172A;
    --ra-slate-800: #1E293B;
    --ra-slate-700: #334155;
    --ra-slate-600: #475569;
    --ra-slate-500: #64748B;
    --ra-slate-400: #94A3B8;
    --ra-slate-200: #E2E8F0;
    --ra-slate-100: #F1F5F9;
    --ra-slate-50: #F8FAFC;
    --ra-white: #FFFFFF;
    
    --ra-emerald-bg: #ECFDF5;
    --ra-emerald-border: #A7F3D0;
    --ra-emerald-text: #065F46;
    
    --ra-amber-bg: #FFFBEB;
    --ra-amber-border: #FDE68A;
    --ra-amber-text: #92400E;
    
    --ra-rose-bg: #FFF1F2;
    --ra-rose-border: #FECDD3;
    --ra-rose-text: #9F1239;
    
    --ra-font: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --ra-mono: 'JetBrains Mono', monospace;
}

html, body, [class*="css"] {
    font-family: var(--ra-font);
}

.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--ra-slate-50);
    color: var(--ra-slate-800);
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1200px;
    padding: 2.2rem 2.5rem 4.5rem;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: var(--ra-white);
    border-right: 1px solid var(--ra-slate-200);
}

[data-testid="stSidebar"] .block-container {
    padding: 2rem 1.25rem;
}

/* App Header & Branding */
.ra-brand-header {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding-bottom: 1.25rem;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid var(--ra-slate-200);
}

.ra-brand-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
    border-radius: 10px;
    color: white;
    font-weight: 800;
    font-size: 1.2rem;
    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
}

.ra-brand-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--ra-slate-900);
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.ra-brand-tagline {
    font-size: 0.76rem;
    color: var(--ra-slate-500);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Hero Section */
.ra-hero-container {
    margin-bottom: 2rem;
}

.ra-hero-eyebrow {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ra-accent);
    background: var(--ra-accent-light);
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    margin-bottom: 0.75rem;
}

.ra-hero-heading {
    font-size: clamp(2rem, 3.5vw, 2.75rem);
    font-weight: 800;
    color: var(--ra-slate-900);
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin: 0 0 0.5rem;
}

.ra-hero-subtitle {
    font-size: 1.1rem;
    color: var(--ra-slate-600);
    line-height: 1.6;
    max-width: 780px;
    margin: 0;
}

/* Feature & Overview Cards */
.ra-card {
    background: var(--ra-white);
    border: 1px solid var(--ra-slate-200);
    border-radius: 12px;
    padding: 1.35rem 1.5rem;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
    transition: all 0.2s ease;
    height: 100%;
}

.ra-card:hover {
    border-color: #CBD5E1;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.ra-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--ra-slate-900);
    margin: 0 0 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.ra-card-desc {
    font-size: 0.9rem;
    color: var(--ra-slate-600);
    line-height: 1.5;
    margin: 0;
}

/* Badge Pills */
.ra-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.22rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0.2rem 0.25rem 0.2rem 0;
    line-height: 1.3;
}

.ra-pill-green {
    background: var(--ra-emerald-bg);
    border: 1px solid var(--ra-emerald-border);
    color: var(--ra-emerald-text);
}

.ra-pill-red {
    background: var(--ra-rose-bg);
    border: 1px solid var(--ra-rose-border);
    color: var(--ra-rose-text);
}

.ra-pill-amber {
    background: var(--ra-amber-bg);
    border: 1px solid var(--ra-amber-border);
    color: var(--ra-amber-text);
}

.ra-pill-blue {
    background: var(--ra-accent-light);
    border: 1px solid #BFDBFE;
    color: #1E40AF;
}

/* Score Hero Display */
.ra-score-card {
    background: linear-gradient(135deg, #1E3A8A 0%, #172554 100%);
    border-radius: 16px;
    padding: 1.8rem;
    color: white;
    box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.25);
    margin-bottom: 1.5rem;
}

.ra-score-number {
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.04em;
    color: #FFFFFF;
}

.ra-score-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #93C5FD;
    font-weight: 700;
    margin-bottom: 0.35rem;
}

.ra-score-explanation {
    font-size: 0.92rem;
    color: #E2E8F0;
    line-height: 1.55;
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
}

/* Action Plan & Bullet Items */
.ra-action-item {
    background: var(--ra-white);
    border: 1px solid var(--ra-slate-200);
    border-left: 4px solid var(--ra-accent);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.85rem;
}

.ra-action-item.priority-high {
    border-left-color: #E11D48;
}

.ra-action-item.priority-medium {
    border-left-color: #D97706;
}

.ra-action-item.priority-low {
    border-left-color: #2563EB;
}

.ra-bullet-box {
    background: var(--ra-slate-50);
    border: 1px solid var(--ra-slate-200);
    border-radius: 10px;
    padding: 1.15rem;
    margin-bottom: 1rem;
}

.ra-bullet-original {
    color: var(--ra-slate-600);
    font-size: 0.9rem;
    text-decoration: line-through;
    margin-bottom: 0.5rem;
}

.ra-bullet-suggested {
    color: var(--ra-emerald-text);
    font-weight: 600;
    font-size: 0.96rem;
    background: var(--ra-emerald-bg);
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    margin-bottom: 0.4rem;
    border-left: 3px solid #059669;
}

.ra-bullet-why {
    font-size: 0.84rem;
    color: var(--ra-slate-500);
    font-style: italic;
}

/* Button & Form Overrides */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stButton"] button[kind="primaryFormSubmit"] {
    background: #1E3A8A;
    color: #FFFFFF;
    font-weight: 700;
    border-radius: 8px;
    border: none;
    padding: 0.65rem 1.5rem;
    box-shadow: 0 4px 6px -1px rgba(30, 58, 138, 0.2);
    transition: all 0.15s ease;
}

[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stButton"] button[kind="primaryFormSubmit"]:hover {
    background: #2563EB;
    box-shadow: 0 6px 12px -2px rgba(37, 99, 235, 0.3);
}

[data-testid="stButton"] button[kind="secondary"] {
    border-radius: 8px;
    font-weight: 600;
}

/* File Uploader Clean Styling */
[data-testid="stFileUploaderDropzone"] {
    background: var(--ra-white);
    border: 2px dashed #CBD5E1;
    border-radius: 12px;
    padding: 1.5rem;
    transition: all 0.2s ease;
}

[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--ra-accent);
    background: var(--ra-accent-light);
}

/* Responsive adjust */
@media (max-width: 768px) {
    .block-container {
        padding: 1.5rem 1rem 3rem;
    }
    .ra-hero-heading {
        font-size: 1.85rem;
    }
    .ra-score-number {
        font-size: 2.5rem;
    }
}
</style>
"""


def apply_theme() -> None:
    """Inject shared professional CSS for the Resume Analyser application."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
