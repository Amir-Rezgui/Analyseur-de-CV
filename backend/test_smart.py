"""Quick end-to-end test with a realistic French job description."""

import sys
sys.path.insert(0, '.')

from core.skill_extractor import SkillExtractor
from core.scorer import Scorer

extractor = SkillExtractor()
scorer = Scorer()

# ── Realistic French JD with lots of noise ──
job_desc = """
Développeur Full Stack - Python / React (H/F)
CDI · Paris 9ème · 45-55K€

Nous recherchons un(e) développeur(se) Full Stack pour rejoindre notre équipe produit.

Profil recherché :
- Vous êtes passionné(e) par le développement web et les nouvelles technologies
- Vous faites preuve de rigueur, d'autonomie et de curiosité intellectuelle
- Vous avez un excellent esprit d'équipe et de bonnes capacités de communication
- Vous êtes force de proposition et avez le goût du challenge

Compétences requises :
- Python (3 ans minimum), JavaScript / TypeScript
- React.js ou Vue.js
- PostgreSQL, Redis
- Docker, Git
- AWS ou équivalent cloud
- Méthodologie Agile / Scrum
- Anglais courant

Compétences appréciées :
- GraphQL, Kubernetes
- Expérience en data engineering (dbt, Airflow)
- CI/CD (GitHub Actions, GitLab CI)
"""

# ── A realistic CV text ──
cv_text = """
Développeur Full Stack · 4 ans d'expérience

COMPÉTENCES TECHNIQUES
Langages: Python, JavaScript, TypeScript, SQL
Frontend: React.js, Next.js, HTML5, CSS3, TailwindCSS
Backend: FastAPI, Django, Node.js, Express
Bases de données: PostgreSQL, MongoDB, Redis
DevOps: Docker, Git, GitHub Actions, AWS (EC2, S3, Lambda)
Outils: Jira, Confluence, Figma, VS Code

EXPÉRIENCE
Lead Developer · Startup Tech · 2022-2024
- Développement d'une plateforme SaaS en React/TypeScript + FastAPI
- Mise en place CI/CD avec GitHub Actions et déploiement sur AWS
- Gestion de base de données PostgreSQL avec 500K+ utilisateurs

Développeur Python · Agence Web · 2020-2022
- Développement d'APIs RESTful avec Django et FastAPI
- Intégration de systèmes de paiement et gestion de Redis
- Participation à des sprints Agile/Scrum

FORMATION
Master Informatique · Université Paris-Saclay · 2020

LANGUES
Français (natif), Anglais (courant), Espagnol (intermédiaire)
"""

print("=" * 60)
print("EXTRACTION DES COMPÉTENCES")
print("=" * 60)

# Extract from JD
job_skills = extractor.extract_skills(job_desc, is_job_posting=True)
dynamic_job = extractor.extract_dynamic_criteria(job_desc, job_skills)
job_skills.extend(dynamic_job)

print(f"\n--- JOB SKILLS ({len(job_skills)} trouvees) ---")
for s in job_skills:
    tier_icon = "RED" if s.tier == "critical" else "BLUE" if s.tier == "important" else "GRAY"
    req_flag = "REQ" if s.is_required else "OPT"
    # Ensure ascii safe print
    name_safe = s.name.encode('ascii', 'ignore').decode('ascii')
    cat_safe = s.category_label.encode('ascii', 'ignore').decode('ascii')
    print(f"  {tier_icon} [{s.tier:9s}] [{req_flag}] {name_safe:30s} ({cat_safe})")

# Extract from CV
cv_skills = extractor.extract_skills(cv_text, is_job_posting=False)
dynamic_cv = extractor.find_specific_skills(cv_text, dynamic_job)
cv_skills.extend(dynamic_cv)

print(f"\n--- CV SKILLS ({len(cv_skills)} trouvees) ---")
for s in cv_skills:
    tier_icon = "RED" if s.tier == "critical" else "BLUE" if s.tier == "important" else "GRAY"
    name_safe = s.name.encode('ascii', 'ignore').decode('ascii')
    cat_safe = s.category_label.encode('ascii', 'ignore').decode('ascii')
    print(f"  {tier_icon} [{s.tier:9s}] {name_safe:30s} ({cat_safe})")

# Score
print("\n" + "=" * 60)
print("SCORING")
print("=" * 60)

result = scorer.calculate_score(cv_skills, job_skills)

overall_score = result.overall_score
classification = result.classification.encode('ascii', 'ignore').decode('ascii')
print(f"\n  SCORE GLOBAL: {overall_score:.1f}% - {classification}")
print(f"  Matchees: {result.total_matched} / {result.total_required}")
print(f"  Synonymes: {result.total_synonyms}")
print(f"  Proches: {result.total_related}")
noise_safe = [n.encode('ascii', 'ignore').decode('ascii') for n in result.noise_skills_ignored]
print(f"  Noise ignore: {noise_safe}")

print("\n--- CATEGORIES ---")
for cs in result.category_scores:
    tier_icon = "RED" if cs.tier == "critical" else "BLUE" if cs.tier == "important" else "GRAY"
    cat_label_safe = cs.category_label.encode('ascii', 'ignore').decode('ascii')
    print(f"  {tier_icon} {cat_label_safe:35s} {cs.match_ratio*100:5.1f}%  "
          f"(matched={cs.matched_skills}, syn={cs.synonym_skills}, rel={cs.related_skills}, miss={cs.missing_skills})")

print("\n--- FORCES ---")
for s in result.strengths:
    s_safe = s.encode('ascii', 'ignore').decode('ascii')
    print(f"  [+] {s_safe}")

print("\n--- FAIBLESSES ---")
for w in result.weaknesses:
    w_safe = w.encode('ascii', 'ignore').decode('ascii')
    print(f"  [-] {w_safe}")

print("\n--- RECOMMANDATIONS ---")
for r in result.recommendations:
    r_safe = r.encode('ascii', 'ignore').decode('ascii')
    print(f"  [*] {r_safe}")
