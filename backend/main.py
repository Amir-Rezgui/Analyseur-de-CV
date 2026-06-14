"""
CV Fit Analyzer — FastAPI Backend

Endpoints:
  POST /api/analyze       → Upload CV + job description → full scoring result
  GET  /api/report/pdf    → Download PDF report
  GET  /api/report/docx   → Download Word report

Extraction strategy:
  Primary:  OpenAI GPT-4o-mini (structured JSON) via LLMExtractor
  Fallback: Local taxonomy + spaCy via SkillExtractor (used if OpenAI unavailable)
"""

import os
import uuid
import glob
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from core.pdf_parser import PDFParser
from core.skill_extractor import SkillExtractor, ExtractedSkill, TIER_CRITICAL, TIER_IMPORTANT, TIER_NOISE
from core.scorer import Scorer
from core.report_generator import ReportGenerator

# Load .env from project root (one level up from backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

# LLM extractor — initialized lazily to avoid crashing if key is missing at import
_llm_extractor = None
_llm_available = False


def _get_llm_extractor():
    global _llm_extractor, _llm_available
    if _llm_extractor is None:
        try:
            from core.llm_extractor import LLMExtractor
            _llm_extractor = LLMExtractor()
            _llm_available = True
        except Exception as e:
            print(f"[Startup] LLM extractor unavailable: {e}. Using taxonomy fallback.")
            _llm_available = False
    return _llm_extractor if _llm_available else None


# ── Directories ──
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="CV Fit Analyzer API",
    description="CV ↔ Job Description compatibility scoring powered by GPT-4o-mini",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

parser = PDFParser()
taxonomy_extractor = SkillExtractor()
scorer = Scorer()
report_gen = ReportGenerator()

# In-memory session store for report downloads
_sessions: dict = {}


@app.get("/")
async def root():
    _get_llm_extractor()
    return {
        "service": "CV Fit Analyzer",
        "version": "2.0.0",
        "llm_extraction": _llm_available,
        "docs": "/docs",
    }


@app.post("/api/analyze")
async def analyze(
    cv_file: UploadFile = File(..., description="CV in PDF format"),
    job_file: Optional[UploadFile] = File(None, description="Job description PDF (optional)"),
    job_text: Optional[str] = Form(None, description="Job description as plain text"),
):
    """
    Analyze CV vs. job description.

    Accepts:
    - cv_file: PDF (required)
    - job_file OR job_text: one of the two required
    """
    session_id = str(uuid.uuid4())[:8]

    if not job_file and not job_text:
        raise HTTPException(400, "Provide a job description: either a PDF file or plain text.")

    if cv_file.filename and not cv_file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "CV must be a PDF file.")

    # ── Extract CV text ──
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cv_path = UPLOAD_DIR / f"{session_id}_cv.pdf"
    try:
        with open(cv_path, "wb") as f:
            content = await cv_file.read()
            if not content:
                raise HTTPException(400, "CV file is empty.")
            f.write(content)
        cv_text = parser.extract_text(str(cv_path))
    except Exception as e:
        raise HTTPException(400, f"Could not read CV: {e}")
    finally:
        if cv_path.exists():
            os.remove(cv_path)

    # ── Extract job description text ──
    if job_file:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        job_path = UPLOAD_DIR / f"{session_id}_job.pdf"
        try:
            with open(job_path, "wb") as f:
                f.write(await job_file.read())
            jd_text = parser.extract_text(str(job_path))
        except Exception as e:
            raise HTTPException(400, f"Could not read job description PDF: {e}")
        finally:
            if job_path.exists():
                os.remove(job_path)
    else:
        jd_text = job_text

    if not cv_text or len(cv_text.strip()) < 20:
        raise HTTPException(400, "CV appears empty or unreadable.")
    if not jd_text or len(jd_text.strip()) < 20:
        raise HTTPException(400, "Job description appears empty or unreadable.")

    # ── Extraction: LLM primary, taxonomy fallback ──
    llm = _get_llm_extractor()
    llm_cv_data = None
    llm_jd_data = None

    if llm:
        try:
            llm_cv_data = llm.extract_cv(cv_text)
            llm_jd_data = llm.extract_job_description(jd_text)
        except Exception as e:
            print(f"[Analyze] LLM extraction error: {e}. Falling back to taxonomy.")

    if llm_cv_data and llm_jd_data:
        cv_skills, job_skills = _build_skills_from_llm(llm, llm_cv_data, llm_jd_data)
    else:
        cv_skills = taxonomy_extractor.extract_skills(cv_text, is_job_posting=False)
        job_skills = taxonomy_extractor.extract_skills(jd_text, is_job_posting=True)
        dynamic_jd = taxonomy_extractor.extract_dynamic_criteria(jd_text, job_skills)
        job_skills.extend(dynamic_jd)
        dynamic_cv = taxonomy_extractor.find_specific_skills(cv_text, dynamic_jd)
        cv_skills.extend(dynamic_cv)

    # ── Score ──
    result = scorer.calculate_score(cv_skills, job_skills)

    # ── Generate reports ──
    pdf_path = REPORTS_DIR / f"{session_id}_report.pdf"
    docx_path = REPORTS_DIR / f"{session_id}_report.docx"
    try:
        report_gen.generate_pdf(result, str(pdf_path))
        report_gen.generate_docx(result, str(docx_path))
    except Exception as e:
        print(f"[Analyze] Report generation error: {e}")

    _sessions[session_id] = {
        "result": result.to_dict(),
        "pdf_path": str(pdf_path),
        "docx_path": str(docx_path),
    }

    return {
        "session_id": session_id,
        "scoring": result.to_dict(),
        "cv_skills": [s.to_dict() for s in cv_skills],
        "job_skills": [s.to_dict() for s in job_skills],
        "cv_skills_count": len(cv_skills),
        "job_skills_count": len(job_skills),
        "extraction_mode": "llm" if (llm_cv_data and llm_jd_data) else "taxonomy",
        "reports_available": {
            "pdf": f"/api/report/{session_id}/rapport.pdf",
            "docx": f"/api/report/{session_id}/rapport.docx",
        },
    }


@app.get("/api/report/{session_id}/rapport.pdf")
@app.get("/api/report/pdf/{session_id}")
async def download_pdf(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found. Please re-run the analysis.")
    path = _sessions[session_id]["pdf_path"]
    if not os.path.exists(path):
        raise HTTPException(404, "PDF report not available.")

    with open(path, "rb") as f:
        content = f.read()

    # application/octet-stream + Content-Disposition: attachment
    # forces Chrome to save to Downloads instead of opening a preview tab
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="rapport_cv_match.pdf"',
            "Content-Length": str(len(content)),
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.get("/api/report/{session_id}/rapport.docx")
@app.get("/api/report/docx/{session_id}")
async def download_docx(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found. Please re-run the analysis.")
    path = _sessions[session_id]["docx_path"]
    if not os.path.exists(path):
        raise HTTPException(404, "Word report not available.")

    with open(path, "rb") as f:
        content = f.read()

    # Same fix as PDF — octet-stream forces download dialog in all browsers
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="rapport_cv_match.docx"',
            "Content-Length": str(len(content)),
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


def _build_skills_from_llm(llm, cv_data: dict, jd_data: dict):
    """
    Converts LLM-structured output into ExtractedSkill objects compatible
    with the existing Scorer. Bridges the LLM extraction layer to the scoring engine.
    """
    cv_flat = llm.flatten_cv_to_skills(cv_data)
    jd_flat = llm.flatten_jd_to_skills(jd_data)

    def make_skill(name: str, category: str, label: str, tier: str,
                   is_required=False, is_preferred=False) -> ExtractedSkill:
        return ExtractedSkill(
            name=name.lower(),
            original_text=name,
            category=category,
            category_label=label,
            confidence=1.0,
            is_required=is_required,
            is_preferred=is_preferred,
            tier=tier,
        )

    cv_skills = [
        make_skill(s, "llm_extracted", "Extracted from CV", TIER_CRITICAL)
        for s in cv_flat
    ]

    job_skills = []
    for s in jd_flat.get("required", []):
        job_skills.append(make_skill(
            s, "required_skills", "Required Skills", TIER_CRITICAL,
            is_required=True,
        ))
    for s in jd_flat.get("preferred", []):
        job_skills.append(make_skill(
            s, "preferred_skills", "Preferred Skills", TIER_IMPORTANT,
            is_preferred=True,
        ))
    for s in jd_flat.get("nice_to_have", []):
        job_skills.append(make_skill(
            s, "optional_skills", "Nice to Have", TIER_NOISE,
        ))

    return cv_skills, job_skills


@app.on_event("shutdown")
async def cleanup():
    for f in glob.glob(str(UPLOAD_DIR / "*_cv.pdf")) + glob.glob(str(UPLOAD_DIR / "*_job.pdf")):
        try:
            os.remove(f)
        except OSError:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)