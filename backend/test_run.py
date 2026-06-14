import sys
import os
from pathlib import Path

# Add core path
sys.path.append(str(Path(__file__).parent))

from core.pdf_parser import PDFParser
from core.skill_extractor import SkillExtractor
from core.scorer import Scorer
from core.report_generator import ReportGenerator

def main():
    print("Testing backend modules...")
    cv_path = "../test_resume.pdf"
    if not os.path.exists(cv_path):
        print(f"Error: {cv_path} not found.")
        return

    job_text = """
    Nous recherchons un développeur Full Stack Python et React avec des compétences en SQL (PostgreSQL), Docker, Git, et un niveau d'anglais professionnel. Des connaissances en Django ou FastAPI sont requises.
    """

    print("1. Parsing PDF...")
    cv_text = PDFParser.extract_text(cv_path)
    print(f"CV Text length: {len(cv_text)}")

    print("2. Extracting skills...")
    extractor = SkillExtractor()
    cv_skills = extractor.extract_skills(cv_text, is_job_posting=False)
    job_skills = extractor.extract_skills(job_text, is_job_posting=True)
    print(f"CV Skills extracted: {len(cv_skills)}")
    print(f"Job Skills extracted: {len(job_skills)}")

    print("3. Scoring...")
    scorer = Scorer()
    result = scorer.calculate_score(cv_skills, job_skills)
    print(f"Overall Score: {result.overall_score:.1f}%")
    print(f"Classification: {result.classification}")

    print("4. Generating Reports...")
    report_gen = ReportGenerator()
    pdf_path = "test_report.pdf"
    docx_path = "test_report.docx"
    
    report_gen.generate_pdf(result, pdf_path)
    report_gen.generate_docx(result, docx_path)
    
    print(f"PDF Report generated at: {os.path.abspath(pdf_path)}")
    print(f"Word Report generated at: {os.path.abspath(docx_path)}")
    print("Backend test completed successfully!")

if __name__ == "__main__":
    main()
