"""Deterministic, local keyword-based resume analysis."""

import re

from app.services.resume_service import (
    ActionItem,
    ATSCheckItem,
    BulletPointImprovement,
    JobMatch,
    ResumeAnalysis,
    ResumeAnalysisError,
)

TECHNICAL_SKILLS: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "Java": ("java",),
    "JavaScript": ("javascript",),
    "TypeScript": ("typescript",),
    "C#": ("c#", "c sharp"),
    "C++": ("c++", "c plus plus"),
    "SQL": ("sql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb", "mongo db"),
    "Redis": ("redis",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure",),
    "Google Cloud": ("google cloud", "gcp"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Git": ("git",),
    "Linux": ("linux",),
    "REST APIs": ("rest api", "restful api", "rest apis"),
    "FastAPI": ("fastapi",),
    "Flask": ("flask",),
    "Django": ("django",),
    "React": ("react",),
    "Node.js": ("node.js", "nodejs"),
    "HTML": ("html",),
    "CSS": ("css",),
    "Excel": ("excel", "microsoft excel"),
    "Tableau": ("tableau",),
    "Power BI": ("power bi",),
    "Machine Learning": ("machine learning",),
    "Data Analysis": ("data analysis", "data analytics"),
    "Statistics": ("statistics",),
    "Cybersecurity": ("cybersecurity", "information security"),
    "CI/CD": ("ci/cd", "continuous integration", "continuous deployment"),
    "Testing": ("testing", "test automation", "automated testing"),
    "pytest": ("pytest",),
    "TensorFlow": ("tensorflow",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "Apache Spark": ("apache spark", "pyspark", "spark"),
}

SOFT_SKILLS: dict[str, tuple[str, ...]] = {
    "Communication": ("communication",),
    "Leadership": ("leadership", "led a team", "team lead"),
    "Collaboration": ("collaboration", "collaborative"),
    "Teamwork": ("teamwork", "team work"),
    "Problem solving": ("problem solving", "problem-solving"),
    "Critical thinking": ("critical thinking",),
    "Adaptability": ("adaptability", "adaptable"),
    "Time management": ("time management",),
    "Stakeholder management": ("stakeholder management", "stakeholders"),
    "Project management": ("project management",),
    "Agile": ("agile",),
    "Mentoring": ("mentoring", "mentored"),
    "Attention to detail": ("attention to detail",),
}

_STOP_WORDS = frozenset(
    "a an and are as at be by can candidate for from has have in is it its of on "
    "or our the their this to with will you your role position responsibility "
    "responsibilities required requirements preferred years experience skill "
    "skills ability strong excellent work team join looking including across "
    "using support knowledge plus also highly relevant must should".split()
)
_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]*")
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|[\r\n]+")


def _contains_alias(text: str, alias: str) -> bool:
    """Find a literal alias without matching it inside larger words."""
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )
    return pattern.search(text) is not None


def _detect_skills(
    text: str,
    catalog: dict[str, tuple[str, ...]],
) -> list[str]:
    """Return catalog skills that occur literally in the supplied text."""
    return [
        skill
        for skill, aliases in catalog.items()
        if any(_contains_alias(text, alias) for alias in aliases)
    ]


def _extract_keywords(text: str) -> list[str]:
    """Extract up to 40 distinct non-generic literal terms, in source order."""
    terms: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_PATTERN.finditer(text):
        term = match.group().strip("./-+").casefold()
        if len(term) < 3 or term in _STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) == 40:
            break
    return terms


def _evidence_snippets(resume_text: str, skills: list[str]) -> list[str]:
    """Return short resume sentences containing each matched skill."""
    evidence: list[str] = []
    for skill in skills:
        aliases = TECHNICAL_SKILLS.get(skill, SOFT_SKILLS.get(skill, (skill,)))
        for sentence in _SENTENCE_PATTERN.split(resume_text):
            candidate = " ".join(sentence.split())
            if candidate and any(
                _contains_alias(candidate, alias) for alias in aliases
            ):
                evidence.append(f"{skill}: {candidate[:240]}")
                break
        if len(evidence) >= 12:
            break
    return evidence


def _evaluate_local_ats(resume: str) -> list[ATSCheckItem]:
    """Perform deterministic ATS checks on resume structure and contents."""
    checks: list[ATSCheckItem] = []

    # 1. Section headings check
    heading_catalog = {
        "experience": ("experience", "work history", "employment"),
        "education": ("education", "academic", "academics"),
        "skills": ("skills", "technical skills", "skill", "competencies"),
        "projects": ("projects", "project"),
    }
    found_headings = [
        name
        for name, aliases in heading_catalog.items()
        if any(_contains_alias(resume, alias) for alias in aliases)
    ]
    if len(found_headings) >= 3:
        checks.append(
            ATSCheckItem(
                check_name="Standard Section Headings",
                status="pass",
                finding=f"Identified core sections: {', '.join(h.capitalize() for h in found_headings)}.",
                suggestion="Maintain standard headers (e.g. Work Experience, Education, Skills) for clear ATS parsing.",
            )
        )
    else:
        checks.append(
            ATSCheckItem(
                check_name="Standard Section Headings",
                status="warning",
                finding="Some standard resume section headings (Experience, Education, Skills) were not clearly identified.",
                suggestion="Use conventional headings like 'Work Experience', 'Education', and 'Technical Skills'.",
            )
        )

    # 2. Contact info check
    has_email = bool(re.search(r"[\w.-]+@[\w.-]+\.\w+", resume))
    has_phone = bool(
        re.search(
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            resume,
        )
    )
    if has_email or has_phone:
        details = []
        if has_email:
            details.append("email")
        if has_phone:
            details.append("phone")
        checks.append(
            ATSCheckItem(
                check_name="Contact Information",
                status="pass",
                finding=f"Contact information ({', '.join(details)}) was detected in the resume.",
                suggestion="Verify phone number and professional profile links (LinkedIn, GitHub) are up to date.",
            )
        )
    else:
        checks.append(
            ATSCheckItem(
                check_name="Contact Information",
                status="warning",
                finding="No email address format was detected.",
                suggestion="Ensure your email and telephone number are in selectable text at the top of the resume.",
            )
        )

    # 3. Quantifiable metrics check
    numbers = re.findall(
        r"\b(?:\d+%(?:\s+increase|\s+growth)?|\$\d+[\d,.]*|\d+\+?\s+(?:users|customers|clients|projects|engineers|team))\b",
        resume,
        re.IGNORECASE,
    )
    if len(numbers) >= 2:
        checks.append(
            ATSCheckItem(
                check_name="Quantifiable Impact & Metrics",
                status="pass",
                finding=f"Detected measurable metrics and numbers: {', '.join(numbers[:3])}.",
                suggestion="Continue highlighting results with measurable data wherever possible.",
            )
        )
    else:
        checks.append(
            ATSCheckItem(
                check_name="Quantifiable Impact & Metrics",
                status="warning",
                finding="Few quantifiable metrics (percentages, dollar amounts, scale) were detected.",
                suggestion="Add measurable outcomes (e.g., 'reduced latency by 25%', 'managed team of 5').",
            )
        )

    # 4. Length and text density
    char_len = len(resume)
    if 800 <= char_len <= 15000:
        checks.append(
            ATSCheckItem(
                check_name="Resume Text Density",
                status="pass",
                finding=f"Resume content length ({char_len:,} characters) is within typical 1-2 page range.",
                suggestion="Keep content focused and concise.",
            )
        )
    else:
        checks.append(
            ATSCheckItem(
                check_name="Resume Text Density",
                status="warning",
                finding=f"Resume length ({char_len:,} characters) is outside the typical 800-15,000 character range.",
                suggestion="Ensure full resume text was extracted and aims for 1 to 2 pages.",
            )
        )

    return checks


class LocalResumeAnalyzer:
    """Produce deterministic findings without network access or external API calls."""

    def __init__(self, max_resume_chars: int = 30000) -> None:
        """Set the maximum length allowed for resume and job-description text."""
        if max_resume_chars < 1:
            raise ValueError("max_resume_chars must be greater than zero.")
        self._max_resume_chars = max_resume_chars

    def analyze(
        self,
        resume_text: str,
        job_description: str | None = None,
        job_title: str | None = None,
    ) -> ResumeAnalysis:
        """Analyze literal skill phrases and keyword overlap deterministically."""
        resume = resume_text.strip()
        description = job_description.strip() if job_description else ""
        title = job_title.strip() if job_title else ""

        if not resume:
            raise ResumeAnalysisError("Paste or upload resume text before analysis.")
        if len(resume) > self._max_resume_chars:
            raise ResumeAnalysisError(
                f"Resume text exceeds the {self._max_resume_chars:,}-character limit."
            )
        if len(description) > self._max_resume_chars:
            raise ResumeAnalysisError(
                f"Job description exceeds the {self._max_resume_chars:,}-character limit."
            )

        resume_technical = _detect_skills(resume, TECHNICAL_SKILLS)
        resume_soft = _detect_skills(resume, SOFT_SKILLS)
        detected_skills = resume_technical + resume_soft
        resume_terms = {term.casefold() for term in _TOKEN_PATTERN.findall(resume)}

        job_match: JobMatch | None = None
        missing_skills: list[str] = []
        learning_suggestions: list[str] = []
        resume_improvements = [
            "Add verifiable metrics and measurable outcomes to relevant resume bullets.",
            "Use industry-standard role terminology to ensure ATS keyword alignment.",
        ]
        bullet_point_improvements: list[BulletPointImprovement] = []
        warnings: list[str] = [
            "Local analysis mode: semantic parsing and AI reasoning are disabled. Results reflect literal keyword and phrase matching."
        ]

        # Scan for lines that look like bullet points
        raw_lines = [
            line.strip() for line in resume.splitlines() if len(line.strip()) > 25
        ]
        for line in raw_lines[:2]:
            clean_line = line.lstrip("•-*# ").strip()
            bullet_point_improvements.append(
                BulletPointImprovement(
                    original_or_issue=clean_line[:120],
                    suggested_revision=(
                        f"Spearheaded {clean_line[:60].lower()}, achieving measurable efficiency gains and optimizing delivery."
                    ),
                    explanation="Strengthen with a power verb and explicit metrics (STAR framework).",
                )
            )

        if description:
            required_skills = _detect_skills(description, TECHNICAL_SKILLS)
            required_skills += _detect_skills(description, SOFT_SKILLS)
            # Remove duplicates preserving order
            seen_req: set[str] = set()
            unique_req: list[str] = []
            for s in required_skills:
                if s not in seen_req:
                    seen_req.add(s)
                    unique_req.append(s)

            resume_skill_set = set(detected_skills)
            matching_skills = [s for s in unique_req if s in resume_skill_set]
            missing_skills = [s for s in unique_req if s not in resume_skill_set]

            job_terms = _extract_keywords(description)
            matching_keywords = [t for t in job_terms if t in resume_terms]
            missing_keywords = [t for t in job_terms if t not in resume_terms]
            evidence = _evidence_snippets(resume, matching_skills)

            # Explainable score calculation
            total_req = len(unique_req)
            matched_count = len(matching_skills)
            skill_ratio = (matched_count / total_req) if total_req > 0 else 0.5
            kw_ratio = (len(matching_keywords) / len(job_terms)) if job_terms else 0.5
            calc_score = int(round((0.7 * skill_ratio + 0.3 * kw_ratio) * 100))
            calc_score = max(5, min(95, calc_score))

            score_explanation = (
                f"Calculated deterministically from {matched_count}/{total_req} matching catalog skills "
                f"(70% weight) and {len(matching_keywords)}/{len(job_terms)} matched keywords (30% weight). "
                "This indicates keyword coverage, not an objective hiring probability."
            )

            strengths = []
            if matching_skills:
                strengths.append(
                    "Resume explicitly matches catalog skills: "
                    + ", ".join(matching_skills[:8])
                    + "."
                )
            if matching_keywords and not matching_skills:
                strengths.append(
                    "Common terms found in both resume and job description: "
                    + ", ".join(matching_keywords[:8])
                    + "."
                )

            suggestions = []
            if missing_skills:
                suggestions.append(
                    "If you possess this experience, add concrete examples for: "
                    + ", ".join(missing_skills[:8])
                    + "."
                )
            if missing_keywords:
                suggestions.append(
                    "Review job-description keywords and include relevant terms: "
                    + ", ".join(missing_keywords[:8])
                    + "."
                )

            job_match = JobMatch(
                target_role=title or "Target Role",
                fit_summary=(
                    f"Literal keyword analysis identified {len(matching_skills)} matching catalog skills "
                    f"and {len(missing_skills)} missing skills. Context and proficiency are not evaluated in local mode."
                ),
                match_score=calc_score,
                match_score_explanation=score_explanation,
                matching_skills=matching_skills,
                missing_skills=missing_skills,
                insufficiently_evidenced_skills=[
                    s
                    for s in matching_skills
                    if not any(s.lower() in ev.lower() for ev in evidence)
                ],
                job_requirements_summary=unique_req[:10],
                strengths=strengths,
                experience_relevance="Literal match against experience terms; semantic alignment requires Gemini mode.",
                project_relevance="Keyword match against project terms; semantic evaluation requires Gemini mode.",
                role_recommendations=suggestions,
                improvement_suggestions=suggestions,
                matching_keywords=matching_keywords,
                missing_keywords=missing_keywords,
                relevant_evidence=evidence,
            )

            learning_suggestions = [
                f"Consider gaining hands-on proficiency in {skill}."
                for skill in missing_skills[:6]
            ]
            resume_improvements.insert(
                0,
                "Tailor resume highlights with quantifiable results matching the job description.",
            )
        else:
            resume_improvements.append(
                "Add a target role and job description to compare skills and generate a match assessment."
            )

        ats_checks = _evaluate_local_ats(resume)

        skills_summary = (
            ", ".join(detected_skills[:10])
            if detected_skills
            else "no skills from the standard catalog"
        )
        experience_terms = [
            term
            for term in (
                "lead",
                "engineer",
                "developer",
                "manager",
                "architect",
                "internship",
                "project",
            )
            if _contains_alias(resume, term)
        ]
        experience_assessment = (
            "Local keyword scan detected role terms: "
            + (
                ", ".join(experience_terms)
                if experience_terms
                else "general experience terms"
            )
            + ". (Full semantic seniority and trajectory analysis is available in Gemini mode.)"
        )

        action_plan = [
            ActionItem(
                priority="High",
                title="Address Critical Skill Alignment",
                action=(
                    f"Highlight core requirements such as {', '.join(missing_skills[:3])}."
                    if missing_skills
                    else "Ensure primary technical proficiencies are clearly listed in your skills section."
                ),
                impact="Directly improves keyword matching for automated ATS filters.",
            ),
            ActionItem(
                priority="Medium",
                title="Quantify Project Outcomes",
                action="Revise bullets to follow the Action Verb + Context + Result format with numbers.",
                impact="Increases recruiter engagement during manual review.",
            ),
            ActionItem(
                priority="Low",
                title="Verify ATS Formatting",
                action="Confirm standard single-column layout, readable fonts, and conventional section headers.",
                impact="Ensures reliable document parsing across various hiring platforms.",
            ),
        ]

        return ResumeAnalysis(
            analysis_mode="Local keyword-based",
            resume_summary=(
                f"Local keyword scan identified {skills_summary}. Semantic summary requires Gemini mode."
            ),
            technical_skills=resume_technical,
            soft_skills=resume_soft,
            experience_assessment=experience_assessment,
            job_match=job_match,
            bullet_point_improvements=bullet_point_improvements,
            ats_formatting_checks=ats_checks,
            warnings=warnings,
            prioritized_action_plan=action_plan,
            job_recommendations=[],
            missing_skills=missing_skills,
            learning_suggestions=learning_suggestions,
            resume_improvements=resume_improvements,
        )
