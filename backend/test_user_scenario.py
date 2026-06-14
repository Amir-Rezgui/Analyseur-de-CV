"""Test specifically reproducing the user's Drupal / Symfony / React stage scenario."""

import sys
sys.path.insert(0, '.')

from core.skill_extractor import SkillExtractor
from core.scorer import Scorer

extractor = SkillExtractor()
scorer = Scorer()

# The exact JD pasted by the user
jd_text = """
Offre de Stage – Développeur Web (Drupal / Symfony / React)
DorcyWay -Ariana, Tunisie

Description de l'emploi:
DORCYWAY est une société spécialisée dans les solutions digitales et le développement d’applications web.
Dans le cadre du développement de nos activités, nous recherchons un(e) stagiaire Développeur Web motivé(e) pour participer à la conception et au développement de nos applications.

Intitulé du poste: Stagiaire Développeur Web Full Stack (Drupal / Symfony / React)

Missions:
- Développement et maintenance d'applications web sous Drupal, Symfony et React.
- Intégration de maquettes et interfaces utilisateur responsives.
- Création et consommation d'API REST.
- Tests, débogage et correction des anomalies.
- Optimisation des performances des applications.
- Rédaction de documentation technique.
- Soucieuse de la qualité du code produit.

Compétences techniques appréciées:
- PHP 8+
- Drupal 9/10/11
- Symfony
- React.js
- JavaScript / TypeScript
- HTML5 / CSS3
- Git et GitHub/GitLab
- MySQL ou PostgreSQL
- APIs REST
- Docker (un plus)

Qualités personnelles (NOISE):
- Passionnée par le développement web.
- Curieuse et désireuse d'apprendre.
- Rigoureuse et organisée.
- Autonome tout en sachant travailler en équipe.
- Force de proposition.
"""

# A realistic candidate CV containing a GitHub link in the header
cv_text = """
Hassen Ben Ali
El Menzah, Ariana, Tunisie · github.com/hassenba · hassen@email.com

COMPÉTENCES
- Web Frontend: React, Redux, JavaScript, HTML5, CSS3, Tailwind CSS
- Web Backend: PHP, Symfony, Node.js, REST APIs
- Bases de données: MySQL, PostgreSQL
- Outils & DevOps: Git, Docker

PROJETS
- Déploiement d'un site e-commerce en React et Symfony. Code disponible sur github.com/hassenba/shop.
- Développement d'un module Drupal de gestion de contenu.
"""

print("Running user scenario analysis...")
job_skills = extractor.extract_skills(jd_text, is_job_posting=True)
dynamic_job = extractor.extract_dynamic_criteria(jd_text, job_skills)
job_skills.extend(dynamic_job)

cv_skills = extractor.extract_skills(cv_text, is_job_posting=False)
dynamic_cv = extractor.find_specific_skills(cv_text, dynamic_job)
cv_skills.extend(dynamic_cv)

# Run Scoring
result = scorer.calculate_score(cv_skills, job_skills)

print("\n" + "="*50)
print(f"SCORE GLOBAL: {result.overall_score:.1f}% — {result.classification}")
print(f"Compétences matchées: {result.total_matched} / {result.total_required}")
print(f"Synonymes trouvés: {result.total_synonyms}")
print(f"Proches trouvés: {result.total_related}")
print("="*50)

print("\n--- CATÉGORIES RETENUES ---")
for cs in result.category_scores:
    print(f"  [{cs.tier.upper():9s}] {cs.category_label:30s} : {cs.match_ratio*100:3.0f}% "
          f"(Matched: {cs.matched_skills}, Missing: {cs.missing_skills})")

# Check that Github matches
version_control_cats = [cs for cs in result.category_scores if cs.category == "version_control"]
if version_control_cats:
    vc = version_control_cats[0]
    print(f"\nVersion Control status: Matched = {vc.matched_skills}, Missing = {vc.missing_skills}")
    if "github" in vc.matched_skills:
        print("✅ SUCCESS: 'github' matched correctly from the header link!")
    else:
        print("❌ FAILURE: 'github' did not match!")
else:
    print("❌ FAILURE: version_control category not found!")

# Check that business noise categories are suppressed
business_cats = [cs for cs in result.category_scores if cs.category in (
    "marketing", "finance_accounting", "hr_recruitment", "legal", "supply_chain")]

if not business_cats:
    print("✅ SUCCESS: All false-positive business noise categories (Marketing, Supply Chain, HR, Finance) were successfully suppressed!")
else:
    print(f"❌ FAILURE: Some business categories were not suppressed: {[c.category for c in business_cats]}")
