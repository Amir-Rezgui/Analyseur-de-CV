"""
Scoring Engine — Smart, real-world compatible scoring.

Key innovations over naive binary matching:
  1. Tier-weighted scoring: CRITICAL skills matter 5x more than NOISE
  2. Synonym matching: React = ReactJS = React.js (full credit)
  3. Related skill credit: Has Vue but needs React? Partial credit, not zero
  4. Sigmoid normalization: Scores land in realistic 35-92% range
  5. Preferred vs Required distinction: "Nice to have" skills don't tank your score
"""

import math
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from core.skill_extractor import (
    ExtractedSkill, SkillExtractor,
    TIER_CRITICAL, TIER_IMPORTANT, TIER_NOISE,
    SKILL_SYNONYMS, SKILL_RELATIVES,
)


@dataclass
class SkillMatch:
    """Detailed info about how a single skill was matched."""
    name: str
    status: str  # "matched", "synonym", "related", "missing"
    credit: float  # 0.0 - 1.0
    matched_via: str = ""  # what CV skill it matched against


@dataclass
class CategoryScore:
    """Score détaillé pour une catégorie de compétences."""
    category: str
    category_label: str
    weight: float
    tier: str  # critical, important, noise
    matched_skills: List[str]
    synonym_skills: List[dict]  # [{"job": x, "cv": y}]
    related_skills: List[dict]  # [{"job": x, "cv": y}]
    missing_skills: List[str]
    extra_skills: List[str]  # Compétences du CV non requises
    match_ratio: float  # 0.0 - 1.0 (includes partial credit)
    raw_ratio: float    # 0.0 - 1.0 (exact matches only)
    weighted_score: float  # contribution au score final
    skill_details: List[SkillMatch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category, "category_label": self.category_label,
            "weight": round(self.weight, 3),
            "tier": self.tier,
            "matched_skills": self.matched_skills,
            "synonym_skills": self.synonym_skills,
            "related_skills": self.related_skills,
            "missing_skills": self.missing_skills,
            "extra_skills": self.extra_skills,
            "match_ratio": round(self.match_ratio, 3),
            "raw_ratio": round(self.raw_ratio, 3),
            "weighted_score": round(self.weighted_score, 3),
            "match_count": len(self.matched_skills) + len(self.synonym_skills),
            "required_count": len(self.matched_skills) + len(self.synonym_skills) + len(self.related_skills) + len(self.missing_skills),
        }


@dataclass
class ScoringResult:
    """Résultat complet du scoring."""
    overall_score: float  # 0-100
    classification: str  # Excellent, Bon, Moyen, Faible
    category_scores: List[CategoryScore] = field(default_factory=list)
    total_matched: int = 0
    total_required: int = 0
    total_extra: int = 0
    total_synonyms: int = 0
    total_related: int = 0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    noise_skills_ignored: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "classification": self.classification,
            "category_scores": [c.to_dict() for c in self.category_scores],
            "total_matched": self.total_matched,
            "total_required": self.total_required,
            "total_extra": self.total_extra,
            "total_synonyms": self.total_synonyms,
            "total_related": self.total_related,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "noise_skills_ignored": self.noise_skills_ignored,
        }


class Scorer:
    """
    Real-world scoring engine.
    
    Tier weights:
      CRITICAL  → full weight (these are the skills that actually matter)
      IMPORTANT → 40% weight (methodologies, certifications — nice but secondary)
      NOISE     → 5% weight  (generic soft skills — displayed but barely counted)
    
    Matching credits:
      Exact match  → 1.0
      Synonym      → 0.9 (React = ReactJS)
      Related      → 0.4 (Has Vue, needs React)
      Missing      → 0.0
      Preferred    → penalty is halved (it was just "nice to have")
    """

    # Base weights per category (before tier adjustment)
    CATEGORY_WEIGHTS = {
        "programming_languages": 0.16,
        "web_frontend": 0.12,
        "web_backend": 0.14,
        "databases": 0.12,
        "cloud_devops": 0.12,
        "data_science": 0.12,
        "mobile": 0.08,
        "testing": 0.05,
        "security": 0.05,
        "architecture": 0.04,
        "version_control": 0.03,
        "project_management": 0.05,
        "design": 0.04,
        "languages": 0.04,
        "certifications": 0.03,
        "marketing": 0.08,
        "finance_accounting": 0.08,
        "sales": 0.08,
        "hr_recruitment": 0.08,
        "legal": 0.08,
        "supply_chain": 0.08,
        "soft_skills": 0.02,  # deliberately low
        "dynamic_criteria": 0.06,
    }

    # Tier multipliers — NOISE gets crushed
    TIER_MULTIPLIERS = {
        TIER_CRITICAL: 1.0,
        TIER_IMPORTANT: 0.4,
        TIER_NOISE: 0.05,
    }

    # Credit for different match types
    CREDIT_EXACT = 1.0
    CREDIT_SYNONYM = 0.9
    CREDIT_RELATED = 0.4
    CREDIT_MISSING = 0.0

    CLASSIFICATIONS = [
        (82, "Excellent", "🟢"),
        (65, "Bon", "🔵"),
        (45, "Moyen", "🟡"),
        (0, "Faible", "🔴"),
    ]

    def calculate_score(
        self,
        cv_skills: List[ExtractedSkill],
        job_skills: List[ExtractedSkill],
    ) -> ScoringResult:
        """
        Calcule le score de compatibilité entre un CV et une fiche de poste.
        Uses smart tier weighting, synonym matching, and related-skill credit.
        """
        # Build skill name sets
        cv_names = {s.name for s in cv_skills}
        job_names = {s.name for s in job_skills}
        
        # Find synonyms and relatives across ALL skills
        extractor = SkillExtractor()
        all_synonym_matches, all_relative_matches = extractor.find_synonyms_and_relatives(
            cv_names, job_names
        )
        
        # Group by category
        cv_by_cat = self._group_by_category(cv_skills)
        job_by_cat = self._group_by_category(job_skills)
        
        # ── Cross-Domain Category Filtering ──
        # False positives like "rh", "conformité" show up in tech JDs because the
        # taxonomy hits generic words in the job description body text.
        # Strategy: for a tech-dominant posting, be very aggressive about removing
        # business categories — they need at least 4 distinct skills to be credible.
        TECH_DOMAINS = {
            "programming_languages", "web_frontend", "web_backend", "databases",
            "cloud_devops", "data_science", "mobile", "testing", "security",
            "architecture", "version_control", "dynamic_criteria"
        }
        BUSINESS_DOMAINS = {
            "marketing", "finance_accounting", "sales", "hr_recruitment",
            "legal", "supply_chain"
        }
        # These categories should NEVER appear in a tech job unless they are
        # genuinely dominant (e.g. an HR-tech platform that requires both).
        TECH_JOB_HARD_BLOCK = {"hr_recruitment", "legal", "supply_chain"}
        
        tech_count = 0
        business_count = 0
        for cat, skills in job_by_cat.items():
            if cat in TECH_DOMAINS:
                tech_count += len(skills)
            elif cat in BUSINESS_DOMAINS:
                business_count += len(skills)
                
        primary_domain = "TECH" if tech_count >= business_count else "BUSINESS"
        
        filtered_job_by_cat = {}
        for cat, skills in job_by_cat.items():
            if primary_domain == "TECH" and cat in BUSINESS_DOMAINS:
                # Hard block: HR, Legal, Supply chain never appear in tech postings
                # unless the entire job is about those domains (which means
                # business_count would be > tech_count, handled above).
                if cat in TECH_JOB_HARD_BLOCK:
                    job_skills = [js for js in job_skills if js.category != cat]
                    continue
                # Soft block: other business categories need 4+ skills to be credible
                if len(skills) < 4:
                    job_skills = [js for js in job_skills if js.category != cat]
                    continue
            # Business job: suppress tech categories with < 2 skills
            if primary_domain == "BUSINESS" and cat in TECH_DOMAINS:
                if len(skills) < 2 and cat not in ("version_control", "programming_languages"):
                    job_skills = [js for js in job_skills if js.category != cat]
                    continue
            filtered_job_by_cat[cat] = skills
            
        job_by_cat = filtered_job_by_cat
        
        # Update CV names and Job names to match filtered list
        cv_names = {s.name for s in cv_skills}
        job_names = {s.name for s in job_skills}
        
        # Determine tier for each category based on the majority of its skills
        cat_tiers = {}
        for cat, skills in job_by_cat.items():
            tier_counts = {TIER_CRITICAL: 0, TIER_IMPORTANT: 0, TIER_NOISE: 0}
            for skill_name in skills:
                for js in job_skills:
                    if js.name == skill_name:
                        tier_counts[js.tier] = tier_counts.get(js.tier, 0) + 1
                        break
            cat_tiers[cat] = max(tier_counts, key=tier_counts.get)

        # Calculate per-category scores
        category_scores: List[CategoryScore] = []
        total_matched = 0
        total_required = 0
        total_extra = 0
        total_synonyms = 0
        total_related = 0
        noise_skills = []

        # Compute active weights with tier multipliers
        active_weights = {}
        total_weight = 0
        for cat in job_by_cat:
            base_w = self.CATEGORY_WEIGHTS.get(cat, 0.05)
            tier = cat_tiers.get(cat, TIER_IMPORTANT)
            tier_mult = self.TIER_MULTIPLIERS.get(tier, 0.4)
            w = base_w * tier_mult
            active_weights[cat] = w
            total_weight += w

        # Normalize weights to sum to 1.0
        if total_weight > 0:
            for cat in active_weights:
                active_weights[cat] /= total_weight

        for cat, job_cat_skills in job_by_cat.items():
            cv_cat_skills = cv_by_cat.get(cat, set())
            tier = cat_tiers.get(cat, TIER_IMPORTANT)
            
            # Compute matches with synonym/related credit
            exact_matched = job_cat_skills & cv_cat_skills
            remaining = job_cat_skills - exact_matched
            
            synonym_matches_in_cat = []
            related_matches_in_cat = []
            truly_missing = []
            
            for skill_name in remaining:
                if skill_name in all_synonym_matches:
                    synonym_matches_in_cat.append({
                        "job": skill_name,
                        "cv": all_synonym_matches[skill_name]
                    })
                elif skill_name in all_relative_matches:
                    related_matches_in_cat.append({
                        "job": skill_name,
                        "cv": all_relative_matches[skill_name]
                    })
                else:
                    truly_missing.append(skill_name)
            
            extra = cv_cat_skills - job_cat_skills
            
            # Calculate effective match ratio with weighted credits
            total_in_cat = len(job_cat_skills)
            if total_in_cat == 0:
                ratio = 0
            else:
                credit = (
                    len(exact_matched) * self.CREDIT_EXACT +
                    len(synonym_matches_in_cat) * self.CREDIT_SYNONYM +
                    len(related_matches_in_cat) * self.CREDIT_RELATED +
                    len(truly_missing) * self.CREDIT_MISSING
                )
                ratio = credit / total_in_cat

            # Check if skills were preferred (reduce penalty for missing preferred)
            preferred_missing = []
            required_missing = []
            for skill_name in truly_missing:
                is_pref = False
                for js in job_skills:
                    if js.name == skill_name and js.is_preferred:
                        is_pref = True
                        break
                if is_pref:
                    preferred_missing.append(skill_name)
                else:
                    required_missing.append(skill_name)
            
            # Boost ratio slightly for preferred-only misses
            if total_in_cat > 0 and preferred_missing:
                # Give 30% credit for preferred skills (they shouldn't tank the score)
                preferred_credit = len(preferred_missing) * 0.3
                ratio = (
                    len(exact_matched) * self.CREDIT_EXACT +
                    len(synonym_matches_in_cat) * self.CREDIT_SYNONYM +
                    len(related_matches_in_cat) * self.CREDIT_RELATED +
                    preferred_credit
                ) / total_in_cat

            raw_ratio = len(exact_matched) / total_in_cat if total_in_cat > 0 else 0
            weight = active_weights.get(cat, 0.05)
            weighted = ratio * weight

            label = self._get_category_label(cat, job_skills)
            
            # Track noise
            if tier == TIER_NOISE:
                noise_skills.extend(truly_missing)

            category_scores.append(CategoryScore(
                category=cat, category_label=label, weight=weight,
                tier=tier,
                matched_skills=sorted(exact_matched),
                synonym_skills=synonym_matches_in_cat,
                related_skills=related_matches_in_cat,
                missing_skills=sorted(truly_missing),
                extra_skills=sorted(extra),
                match_ratio=min(1.0, ratio),
                raw_ratio=raw_ratio,
                weighted_score=weighted,
            ))

            total_matched += len(exact_matched) + len(synonym_matches_in_cat)
            total_required += len(job_cat_skills)
            total_extra += len(extra)
            total_synonyms += len(synonym_matches_in_cat)
            total_related += len(related_matches_in_cat)

        # Raw weighted score (0-1)
        raw_score = sum(cs.weighted_score for cs in category_scores)

        # Apply sigmoid normalization for realistic scores
        # This prevents extreme 0% or 100% and centers around 50-65%
        normalized = self._sigmoid_normalize(raw_score)
        
        # Apply bonuses/penalties
        bonus = self._calculate_bonus(category_scores, cv_skills, job_skills)
        final_score = min(95, max(8, (normalized * 100) + bonus))

        # Classification
        classification = "Faible"
        for threshold, label, _ in self.CLASSIFICATIONS:
            if final_score >= threshold:
                classification = label
                break

        # Generate insights
        strengths = self._generate_strengths(category_scores)
        weaknesses = self._generate_weaknesses(category_scores)
        recommendations = self._generate_recommendations(category_scores, classification)

        # Sort categories: critical first, then by weight
        category_scores.sort(key=lambda c: (
            0 if c.tier == TIER_CRITICAL else 1 if c.tier == TIER_IMPORTANT else 2,
            -c.weight,
        ))

        return ScoringResult(
            overall_score=final_score, classification=classification,
            category_scores=category_scores,
            total_matched=total_matched, total_required=total_required,
            total_extra=total_extra,
            total_synonyms=total_synonyms, total_related=total_related,
            strengths=strengths, weaknesses=weaknesses,
            recommendations=recommendations,
            noise_skills_ignored=noise_skills,
        )

    def _sigmoid_normalize(self, raw: float) -> float:
        """
        Apply sigmoid-like normalization to get realistic scores.
        
        Maps raw weighted score (0-1) to a more realistic range:
        - 0.0 raw → ~15% final
        - 0.3 raw → ~40% final
        - 0.5 raw → ~55% final
        - 0.7 raw → ~72% final
        - 0.9 raw → ~85% final
        - 1.0 raw → ~92% final
        
        This prevents scores from being too extreme in either direction.
        """
        if raw <= 0:
            return 0.15
        if raw >= 1.0:
            return 0.92
        
        # Modified sigmoid: steeper in the middle, compressed at extremes
        # f(x) = 1 / (1 + e^(-k*(x-c))) scaled to our desired range
        k = 6.0  # steepness
        c = 0.45  # center point
        sigmoid = 1.0 / (1.0 + math.exp(-k * (raw - c)))
        
        # Scale to realistic range [0.15, 0.92]
        min_score = 0.15
        max_score = 0.92
        return min_score + (max_score - min_score) * sigmoid

    def _group_by_category(self, skills: List[ExtractedSkill]) -> Dict[str, Set[str]]:
        grouped: Dict[str, Set[str]] = {}
        for s in skills:
            grouped.setdefault(s.category, set()).add(s.name)
        return grouped

    def _get_category_label(self, category: str, skills: List[ExtractedSkill]) -> str:
        for s in skills:
            if s.category == category:
                return s.category_label
        return category.replace("_", " ").title()

    def _calculate_bonus(self, cat_scores, cv_skills, job_skills) -> float:
        bonus = 0.0
        
        # Bonus: >80% match on CRITICAL categories
        critical_cats = [cs for cs in cat_scores if cs.tier == TIER_CRITICAL]
        if critical_cats:
            avg_critical = sum(cs.match_ratio for cs in critical_cats) / len(critical_cats)
            if avg_critical > 0.8:
                bonus += 4.0
            elif avg_critical > 0.6:
                bonus += 2.0
        
        # Bonus: languages all matched
        lang_scores = [cs for cs in cat_scores if cs.category == "languages"]
        if lang_scores and lang_scores[0].match_ratio == 1.0:
            bonus += 2.0
        
        # Penalty: <20% match on critical tech skills
        tech_cats = [cs for cs in cat_scores if cs.category in (
            "programming_languages", "web_frontend", "web_backend", "databases")]
        if tech_cats:
            avg_tech = sum(cs.match_ratio for cs in tech_cats) / len(tech_cats)
            if avg_tech < 0.2:
                bonus -= 8.0
            elif avg_tech < 0.3:
                bonus -= 4.0
        
        # Bonus: has synonym matches (shows versatility)
        total_syns = sum(len(cs.synonym_skills) for cs in cat_scores)
        if total_syns > 0:
            bonus += min(3.0, total_syns * 1.0)
        
        # Bonus: has related skills (shows adjacent knowledge)
        total_rels = sum(len(cs.related_skills) for cs in cat_scores)
        if total_rels > 0:
            bonus += min(2.0, total_rels * 0.5)
        
        return bonus

    def _generate_strengths(self, cat_scores: List[CategoryScore]) -> List[str]:
        strengths = []
        for cs in cat_scores:
            if cs.tier == TIER_NOISE:
                continue  # Don't praise soft skill matches
            if cs.match_ratio >= 0.8 and cs.matched_skills:
                total = len(cs.matched_skills) + len(cs.synonym_skills) + len(cs.related_skills) + len(cs.missing_skills)
                matched_count = len(cs.matched_skills) + len(cs.synonym_skills)
                strengths.append(
                    f"Excellente couverture en {cs.category_label} "
                    f"({matched_count}/{total} compétences)"
                )
            elif cs.synonym_skills and cs.match_ratio >= 0.6:
                syn_names = [s["cv"] for s in cs.synonym_skills]
                strengths.append(
                    f"Bonne couverture en {cs.category_label} "
                    f"(compétences équivalentes: {', '.join(syn_names)})"
                )
        return strengths[:5]

    def _generate_weaknesses(self, cat_scores: List[CategoryScore]) -> List[str]:
        weaknesses = []
        for cs in sorted(cat_scores, key=lambda c: c.match_ratio):
            if cs.tier == TIER_NOISE:
                continue  # Don't report soft skill gaps as weaknesses
            if cs.match_ratio < 0.5 and cs.missing_skills:
                weaknesses.append(
                    f"Lacunes en {cs.category_label}: {', '.join(cs.missing_skills[:5])}"
                )
        return weaknesses[:5]

    def _generate_recommendations(self, cat_scores, classification) -> List[str]:
        recs = []
        if classification in ("Faible", "Moyen"):
            for cs in cat_scores:
                if cs.tier == TIER_NOISE:
                    continue  # Don't recommend learning "rigueur" lmao
                if cs.missing_skills and cs.tier == TIER_CRITICAL:
                    recs.append(
                        f"Priorité: développer les compétences en {cs.category_label}: "
                        f"{', '.join(cs.missing_skills[:3])}"
                    )
                elif cs.missing_skills and cs.tier == TIER_IMPORTANT:
                    recs.append(
                        f"Conseillé: acquérir des bases en {cs.category_label}: "
                        f"{', '.join(cs.missing_skills[:3])}"
                    )
            
            # Add related-skill-based recommendations
            for cs in cat_scores:
                if cs.related_skills:
                    for rel in cs.related_skills[:2]:
                        recs.append(
                            f"Le candidat maîtrise {rel['cv']} — une formation sur {rel['job']} (compétence proche) serait pertinente"
                        )
        
        if classification == "Excellent":
            recs.append("Profil très bien aligné avec le poste. Mettre en avant les projets concrets.")
        elif classification == "Bon":
            recs.append("Bon profil. Combler les quelques lacunes identifiées permettrait de maximiser l'adéquation au poste.")
        
        return recs[:6]
