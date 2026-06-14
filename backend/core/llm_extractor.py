"""
LLM Extractor — OpenAI GPT-4o-mini with structured JSON output.

Why LLM over regex/spaCy:
  CVs and job descriptions have wildly inconsistent formatting. A rule-based
  parser breaks on edge cases ("led a team using Agile" → Agile missed by keywords).
  An LLM understands context and can infer competencies from natural language,
  handling French, English, and mixed-language documents equally well.

Fallback strategy:
  If the OpenAI call fails (network error, quota, invalid JSON), the caller
  falls back to the local taxonomy-based extractor — zero downtime.
"""

import json
import os
import re
from typing import Optional

from openai import OpenAI


# ── JSON schemas sent to the model ──

CV_EXTRACTION_PROMPT = """You are a senior technical recruiter parsing a CV/resume.

Extract structured information from the following CV text. Be precise and factual — only extract what is explicitly or clearly implied in the text.

Return ONLY valid JSON matching this exact schema:
{
  "experience": [
    {
      "title": "string",
      "company": "string",
      "duration": "string",
      "technologies": ["string"],
      "responsibilities": ["string"]
    }
  ],
  "projects": [
    {
      "name": "string",
      "tech_stack": ["string"],
      "description": "string"
    }
  ],
  "education": [
    {
      "degree": "string",
      "field": "string",
      "institution": "string",
      "year": "string"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "year": "string"
    }
  ],
  "skills": ["string"],
  "languages": [
    {
      "language": "string",
      "level": "string"
    }
  ]
}

CV TEXT:
"""

JD_EXTRACTION_PROMPT = """You are a senior technical recruiter parsing a job description.

Extract ONLY concrete, verifiable competencies. 
IGNORE ALL of the following — they are noise, not real requirements:
- Personality traits: "rigorous", "curious", "motivated", "dynamic"
- Vague soft skills: "good communicator", "team player", "problem solver"  
- Generic qualities: "autonomous", "organized", "detail-oriented"
- French equivalents: "rigueur", "autonomie", "curiosité", "esprit d'équipe"

Extract ONLY hard, verifiable skills:
- Programming languages (Python, Java, TypeScript…)
- Frameworks and libraries (React, Django, Spring Boot…)
- Databases (PostgreSQL, MongoDB, Redis…)
- Cloud/DevOps tools (AWS, Docker, Kubernetes, CI/CD…)
- Domain methodologies (Agile/Scrum, TDD, REST API design…)
- Certifications (AWS Certified, PMP, CFA…)
- Human languages with required proficiency (French B2, English C1…)

Return ONLY valid JSON:
{
  "required": ["string"],
  "preferred": ["string"],
  "nice_to_have": ["string"],
  "domain": "string",
  "seniority": "string"
}

- "required": skills explicitly marked as required/mandatory
- "preferred": skills marked as "a plus", "appreciated", "ideally"
- "nice_to_have": everything else that is technical but optional
- "domain": primary domain (e.g. "web_fullstack", "data_science", "devops", "mobile", "backend")
- "seniority": detected seniority ("junior", "mid", "senior", "lead", "any")

JOB DESCRIPTION TEXT:
"""


class LLMExtractor:
    """
    OpenAI-powered extraction for CVs and job descriptions.
    Uses GPT-4o-mini for cost efficiency (fast, cheap, structured output quality is sufficient).
    """

    MODEL = "gpt-4o-mini"
    MAX_TOKENS = 2000
    TEMPERATURE = 0.0  # Deterministic: we want consistent, factual extraction

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not set. Add it to your .env file."
            )
        self.client = OpenAI(api_key=api_key)

    def extract_cv(self, cv_text: str) -> Optional[dict]:
        """
        Extract structured CV data using LLM.
        Returns None if extraction fails (caller should fall back to taxonomy extractor).
        """
        return self._call_with_retry(CV_EXTRACTION_PROMPT, cv_text)

    def extract_job_description(self, jd_text: str) -> Optional[dict]:
        """
        Extract required competencies from a job description.
        Returns None if extraction fails.
        """
        return self._call_with_retry(JD_EXTRACTION_PROMPT, jd_text)

    def _call_with_retry(self, prompt: str, text: str, max_retries: int = 2) -> Optional[dict]:
        """
        Call OpenAI with JSON mode and retry once on parse failure.
        Re-prompts with explicit correction instruction if the first response isn't valid JSON.
        """
        messages = [
            {
                "role": "system",
                "content": "You are a precise data extraction engine. Always respond with valid JSON only. No markdown, no explanations, no code blocks.",
            },
            {
                "role": "user",
                "content": prompt + text[:8000],  # Truncate to avoid token limits
            },
        ]

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    response_format={"type": "json_object"},
                )

                raw = response.choices[0].message.content
                return self._parse_json(raw)

            except Exception as e:
                if attempt == max_retries - 1:
                    # Log but don't raise — caller uses fallback
                    print(f"[LLMExtractor] Failed after {max_retries} attempts: {e}")
                    return None
                else:
                    # Retry with correction instruction
                    messages.append({
                        "role": "assistant",
                        "content": "I need to correct my response.",
                    })
                    messages.append({
                        "role": "user",
                        "content": "Your previous response was not valid JSON. Return only a valid JSON object, no other text.",
                    })

        return None

    def _parse_json(self, raw: str) -> Optional[dict]:
        """Parse JSON from LLM response, stripping markdown fences if present."""
        if not raw:
            return None
        # Strip markdown code fences if the model disobeys the system prompt
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def flatten_cv_to_skills(self, cv_data: dict) -> list[str]:
        """
        Convert structured CV JSON into a flat skill list for matching.
        Weights: experience/projects > certifications > skills list (bare mentions).
        """
        if not cv_data:
            return []

        all_skills = []

        # High evidence: technologies used in real work experience
        for exp in cv_data.get("experience", []):
            all_skills.extend(exp.get("technologies", []))

        # High evidence: project tech stacks
        for proj in cv_data.get("projects", []):
            all_skills.extend(proj.get("tech_stack", []))

        # Medium evidence: certifications
        for cert in cv_data.get("certifications", []):
            if cert.get("name"):
                all_skills.append(cert["name"])

        # Low evidence: bare skills section (self-reported, no proof)
        all_skills.extend(cv_data.get("skills", []))

        # Languages (spoken) — normalized
        for lang in cv_data.get("languages", []):
            if lang.get("language"):
                all_skills.append(lang["language"].lower())

        # Deduplicate, normalize
        seen = set()
        result = []
        for s in all_skills:
            normalized = s.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)

        return result

    def flatten_jd_to_skills(self, jd_data: dict) -> dict:
        """
        Returns tiered skills dict: {required: [...], preferred: [...], nice_to_have: [...]}
        Normalized and deduplicated.
        """
        if not jd_data:
            return {"required": [], "preferred": [], "nice_to_have": []}

        def normalize(lst):
            return [s.strip().lower() for s in lst if s and s.strip()]

        return {
            "required": normalize(jd_data.get("required", [])),
            "preferred": normalize(jd_data.get("preferred", [])),
            "nice_to_have": normalize(jd_data.get("nice_to_have", [])),
            "domain": jd_data.get("domain", ""),
            "seniority": jd_data.get("seniority", ""),
        }
