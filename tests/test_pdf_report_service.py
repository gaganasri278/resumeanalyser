"""Unit and integration tests for PDF report generation using ReportLab."""

import json

from app.services.local_resume_service import LocalResumeAnalyzer
from app.services.pdf_report_service import (
    export_analysis_json,
    generate_resume_pdf_report,
)
from app.services.resume_service import (
    ActionItem,
    ATSCheckItem,
    BulletPointImprovement,
    JobMatch,
    ResumeAnalysis,
)


def _make_full_analysis() -> ResumeAnalysis:
    """Create a rich, fully-populated ResumeAnalysis instance for testing."""
    return ResumeAnalysis(
        analysis_mode="Gemini-assisted",
        resume_summary="Senior Software Engineer with 8+ years designing cloud systems.",
        technical_skills=["Python", "Go", "Docker", "Kubernetes", "AWS", "PostgreSQL"],
        soft_skills=["Cross-functional Leadership", "Mentoring", "Agile Collaboration"],
        experience_assessment="Demonstrated progressive technical leadership and scalable systems delivery.",
        job_match=JobMatch(
            target_role="Lead Backend Engineer",
            fit_summary="Exceptional alignment with core backend infrastructure requirements.",
            match_score=92,
            match_score_explanation="Candidate possesses 92% coverage of required cloud orchestration and Python skills.",
            matching_skills=["Python", "Docker", "Kubernetes", "AWS"],
            missing_skills=["Kafka"],
            insufficiently_evidenced_skills=["GraphQL"],
            strengths=[
                "Deep experience in asynchronous Python and microservices architecture.",
                "Strong track record of mentoring junior engineers.",
            ],
            experience_relevance="High relevance to distributed systems engineering.",
            project_relevance="Significant alignment with current cloud modernization initiatives.",
            role_recommendations=[
                "Highlight high-throughput messaging or pub-sub architecture experience.",
                "Detail container performance tuning metrics in recent project bullets.",
            ],
        ),
        bullet_point_improvements=[
            BulletPointImprovement(
                original_or_issue="Maintained database and fixed slow queries.",
                suggested_revision="Engineered query indexing and caching strategy, reducing P99 latency by 45%.",
                explanation="Employs STAR methodology with quantifiable performance impact.",
            ),
            BulletPointImprovement(
                original_or_issue="Responsible for CI/CD deployments.",
                suggested_revision="Automated multi-stage Docker build pipeline across 12 services, cutting deployment time from 35 to 8 minutes.",
                explanation="Replaces passive duty description with active verbs and measurable outcomes.",
            ),
        ],
        ats_formatting_checks=[
            ATSCheckItem(
                check_name="Standard Section Headings",
                status="pass",
                finding="Standard headings (Experience, Education, Skills) are present and recognized.",
                suggestion="Maintain standard naming for seamless ATS categorization.",
            ),
            ATSCheckItem(
                check_name="Contact Information Completeness",
                status="pass",
                finding="Email, phone, and professional LinkedIn URL successfully parsed.",
                suggestion="No changes required.",
            ),
            ATSCheckItem(
                check_name="Bullet Point Quantification",
                status="warning",
                finding="3 of 8 bullet points lack quantitative metrics.",
                suggestion="Incorporate percentages, time savings, or dollar values where possible.",
            ),
            ATSCheckItem(
                check_name="Complex Table Layout",
                status="fail",
                finding="Multi-column layout detected in education section.",
                suggestion="Convert to standard linear layout for legacy scanner reliability.",
            ),
        ],
        warnings=[
            "Scanned document notice: Ensure raw text is selectable.",
            "Missing certifications section: Consider adding relevant AWS certifications.",
        ],
        prioritized_action_plan=[
            ActionItem(
                priority="High",
                title="Quantify Latency & Throughput Metrics",
                action="Incorporate specific percentage improvements into recent role bullets.",
                impact="Increases ATS keyword matching and recruiter attention by ~30%.",
            ),
            ActionItem(
                priority="Medium",
                title="Address Missing Kafka / Pub-Sub Experience",
                action="Explicitly note message queue experience or queueing patterns used.",
                impact="Closes identified core requirement gap for lead role.",
            ),
            ActionItem(
                priority="Low",
                title="Linearize Layout",
                action="Remove multi-column layout in education section.",
                impact="Prevents parsing hiccups on older enterprise ATS portals.",
            ),
        ],
    )


def test_generate_pdf_full_report() -> None:
    """Full analysis model generates valid binary PDF with expected content."""
    analysis = _make_full_analysis()
    pdf_bytes = generate_resume_pdf_report(
        analysis,
        job_title="Lead Backend Engineer",
        generation_date="October 30, 2026",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_missing_fields_and_empty() -> None:
    """PDF generation succeeds without error when optional sections and fields are empty."""
    empty_analysis = ResumeAnalysis(
        analysis_mode="Local keyword-based",
        resume_summary="",
        technical_skills=[],
        soft_skills=[],
        experience_assessment="",
        job_match=None,
        bullet_point_improvements=[],
        ats_formatting_checks=[],
        warnings=[],
        prioritized_action_plan=[],
    )

    pdf_bytes = generate_resume_pdf_report(empty_analysis)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_special_characters_and_entities() -> None:
    """PDF generator escapes XML entities and handles Unicode characters cleanly."""
    special_analysis = ResumeAnalysis(
        analysis_mode="Gemini-assisted",
        resume_summary="Senior C++ & Python Engineer with <script> tags & AT&T experience. Résumé with café & Naïve Bayes.",
        technical_skills=["C++", "C#", "HTML & CSS", "Python <3.12>"],
        soft_skills=["Client Negotiation & Pitching", "Cross-team 'Sync' Meetings"],
        experience_assessment="Demonstrated leadership across EMEA & APAC regions — cutting costs by >40% & <50%.",
        job_match=JobMatch(
            target_role="Fullstack & Cloud Architect (C++ / Python)",
            fit_summary="Strong match for roles requiring C++ & cloud scaling.",
            match_score=85,
            match_score_explanation="Score based on 'C++' & Python skills matching >80% of requirements.",
            matching_skills=["C++", "Python", "SQL & NoSQL"],
            missing_skills=["Kafka & RabbitMQ"],
        ),
        bullet_point_improvements=[
            BulletPointImprovement(
                original_or_issue="Maintained <legacy> C++ codebase & fixed 'memory' leaks.",
                suggested_revision="Optimized C++ & Rust core engine, decreasing P99 latency by >30%.",
                explanation="Details specific technologies & measurable impact.",
            )
        ],
        ats_formatting_checks=[
            ATSCheckItem(
                check_name="Symbols & Entities Audit",
                status="pass",
                finding="Clean text found with & and < characters handled safely.",
                suggestion="Use clean UTF-8 encoding.",
            )
        ],
        warnings=["Notice: Document uses & and 'quotes' in headings."],
        prioritized_action_plan=[
            ActionItem(
                priority="High",
                title="Highlight C++ & Cloud Skills",
                action="Emphasize C++17 & modern async libraries in project descriptions.",
                impact="Maximizes ATS relevance for C++ architecture positions.",
            )
        ],
    )

    pdf_bytes = generate_resume_pdf_report(
        special_analysis,
        job_title="Lead C++ & Python Developer",
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_long_content_multi_page() -> None:
    """Multi-page document with extensive bullets and tables renders without layout errors."""
    many_bullets = [
        BulletPointImprovement(
            original_or_issue=f"Weak responsibility statement #{i} with insufficient metrics.",
            suggested_revision=f"Engineered and deployed system #{i} resulting in {i * 5}% efficiency gain across {i * 2} enterprise teams.",
            explanation=f"Detailed STAR breakdown explaining impact for revision #{i}.",
        )
        for i in range(1, 15)
    ]

    many_ats_checks = [
        ATSCheckItem(
            check_name=f"ATS Audit Metric #{i}",
            status="pass" if i % 3 == 0 else "warning" if i % 3 == 1 else "fail",
            finding=f"Detailed scan finding for check item #{i} regarding section structure.",
            suggestion=f"Actionable guidance recommendation #{i} for candidate.",
        )
        for i in range(1, 12)
    ]

    many_action_items = [
        ActionItem(
            priority="High" if i % 3 == 0 else "Medium" if i % 3 == 1 else "Low",
            title=f"Strategic Objective #{i}",
            action=f"Execute comprehensive resume update #{i} detailing key contributions.",
            impact=f"Improves target metric by {i * 10}%.",
        )
        for i in range(1, 10)
    ]

    long_analysis = ResumeAnalysis(
        analysis_mode="Gemini-assisted",
        resume_summary=(
            "Executive Technology Director with 15+ years of leadership experience spanning enterprise software, "
            "cloud infrastructure, microservices migration, organizational scaling, and budget management. "
            "Pioneered engineering excellence programs across multiple globally distributed teams. "
            * 3
        ),
        technical_skills=[f"TechStackItem_{i}" for i in range(1, 30)],
        soft_skills=[f"SoftSkillItem_{i}" for i in range(1, 20)],
        experience_assessment=(
            "Extensive background in enterprise architecture, people leadership, and product delivery. "
            "Demonstrated success delivering high-availability financial transaction systems. "
            * 3
        ),
        job_match=JobMatch(
            target_role="Vice President of Engineering",
            fit_summary="Exceptional senior executive match.",
            match_score=95,
            matching_skills=[f"TechStackItem_{i}" for i in range(1, 15)],
            missing_skills=["Golang"],
            insufficiently_evidenced_skills=["Kubernetes"],
        ),
        bullet_point_improvements=many_bullets,
        ats_formatting_checks=many_ats_checks,
        prioritized_action_plan=many_action_items,
    )

    pdf_bytes = generate_resume_pdf_report(
        long_analysis,
        job_title="VP of Engineering",
    )
    assert isinstance(pdf_bytes, bytes)
    # A multi-page document is significantly larger than 8 KB
    assert len(pdf_bytes) > 8000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_local_analysis_mode() -> None:
    """PDF generation operates cleanly on deterministic LocalResumeAnalyzer output."""
    analyzer = LocalResumeAnalyzer(max_resume_chars=5000)
    local_result = analyzer.analyze(
        resume_text="Senior Python Developer with 5 years experience in Docker, SQL, and AWS. Contact: test@example.com, (555) 123-4567.",
        job_description="Seeking a Python Engineer with Docker, Kubernetes, and SQL expertise.",
        job_title="Python Engineer",
    )

    pdf_bytes = generate_resume_pdf_report(local_result, job_title="Python Engineer")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_export_analysis_json_preserves_internal_capability() -> None:
    """Internal JSON export helper outputs valid JSON matching the model schema."""
    analysis = _make_full_analysis()
    json_str = export_analysis_json(analysis)

    data = json.loads(json_str)
    assert data["analysis_mode"] == "Gemini-assisted"
    assert data["job_match"]["match_score"] == 92
    assert "Python" in data["technical_skills"]
