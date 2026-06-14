"""
Skill Extractor — Smart extraction with real-world criteria classification.

Key innovation: Classifies job requirements into 3 tiers:
  CRITICAL  — Hard skills, tools, technologies, languages (what actually matters)
  IMPORTANT — Methodologies, domain knowledge, certifications  
  NOISE     — Generic soft skills, personality filler ("rigueur", "curiosité", etc.)

The NOISE tier is displayed but heavily downweighted so generic filler 
doesn't tank someone's score.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

from rapidfuzz import fuzz, process
import spacy


# ── Tier system: What actually matters in a real job application ──
TIER_CRITICAL = "critical"
TIER_IMPORTANT = "important"
TIER_NOISE = "noise"

# Categories that contain hard, measurable, objective skills
CRITICAL_CATEGORIES = {
    "programming_languages", "web_frontend", "web_backend", "databases",
    "cloud_devops", "data_science", "mobile", "testing", "security",
    "architecture", "version_control",
}

# Categories that matter but are secondary
IMPORTANT_CATEGORIES = {
    "project_management", "design", "certifications", "languages",
    "marketing", "finance_accounting", "sales", "hr_recruitment",
    "legal", "supply_chain",
}

# Categories that are mostly filler in a JD
NOISE_CATEGORIES = {
    "soft_skills",
}

# ── Generic filler phrases that no recruiter seriously expects on a CV ──
# These are the "rigueur et désir d'apprendre" type phrases
NOISE_PHRASES_FR = {
    "rigueur", "autonomie", "polyvalence", "curiosité", "motivation",
    "dynamisme", "sérieux", "ponctualité", "assiduité", "bienveillance",
    "pédagogie", "écoute active", "sens du détail", "force de proposition",
    "gestion du stress", "capacité d'adaptation", "prise d'initiative",
    "esprit d'équipe", "esprit analytique", "orientation résultats",
    "gestion des priorités", "travail en équipe", "sens du service",
    "relation client", "client relationship", "esprit critique",
    "proactivité", "réactivité", "disponibilité", "sens de l'organisation",
    "sens des responsabilités", "aisance relationnelle", "bon relationnel",
    "goût du challenge", "désir d'apprendre", "volonté d'apprendre",
    "envie d'apprendre", "passion", "passionné", "enthousiasme",
    "persévérance", "ténacité", "ouverture d'esprit", "humilité",
    "intégrité", "honnêteté", "fiabilité", "consciencieux",
    "minutieux", "méthodique", "organisé", "ordonné", "rigoureux",
    "appliqué", "soigneux", "attentif", "vigilant", "impliqué",
    "engagé", "dévoué", "investi", "motivé", "ambitieux",
    "combatif", "performant", "efficace", "productif", "résistant au stress",
    "sens commercial", "fibre commerciale", "bon communicant",
    "aisance orale", "aisance rédactionnelle", "bonne présentation",
    "esprit de synthèse", "synthèse", "vulgarisation",
    "capacité de travail", "force de travail", "sens de l'écoute",
}

NOISE_PHRASES_EN = {
    "communication", "leadership", "teamwork", "team work", "team player",
    "problem solving", "critical thinking", "analytical thinking",
    "creativity", "adaptability", "time management", "conflict resolution",
    "presentation", "public speaking", "mentoring", "coaching",
    "collaboration", "decision making", "emotional intelligence", "empathy",
    "self-motivation", "initiative", "accountability", "attention to detail",
    "organization", "strategic thinking", "innovation", "customer focus",
    "results oriented", "work ethic", "flexibility", "autonomy",
    "proactivity", "self-starter", "fast learner", "quick learner",
    "eager to learn", "willing to learn", "detail oriented",
    "strong work ethic", "positive attitude", "reliable", "dependable",
    "dedicated", "hardworking", "driven", "passionate", "enthusiastic",
    "goal oriented", "multitasking", "ability to work under pressure",
    "interpersonal skills", "can-do attitude", "go-getter",
    "organizational skills", "strong communication skills",
    "excellent communication", "good communication",
    "ability to work independently", "ability to work in a team",
}

ALL_NOISE_PHRASES = NOISE_PHRASES_FR | NOISE_PHRASES_EN

# ── Related skills mapping for partial credit ──
SKILL_SYNONYMS = {
    "react": {"reactjs", "react.js"},
    "reactjs": {"react", "react.js"},
    "react.js": {"react", "reactjs"},
    "vue": {"vuejs", "vue.js"},
    "vuejs": {"vue", "vue.js"},
    "vue.js": {"vue", "vuejs"},
    "angular": {"angularjs"},
    "angularjs": {"angular"},
    "node.js": {"nodejs"},
    "nodejs": {"node.js"},
    "next.js": {"nextjs"},
    "nextjs": {"next.js"},
    "nest.js": {"nestjs"},
    "nestjs": {"nest.js"},
    "typescript": {"ts"},
    "javascript": {"js"},
    "python": {"py"},
    "postgresql": {"postgres"},
    "postgres": {"postgresql"},
    "k8s": {"kubernetes"},
    "kubernetes": {"k8s"},
    "aws": {"amazon web services"},
    "amazon web services": {"aws"},
    "gcp": {"google cloud"},
    "google cloud": {"gcp"},
    "ci/cd": {"gitlab ci", "github actions", "jenkins", "circleci"},
    "docker": set(),
    "git": set(),
    "golang": {"go"},
    "go": {"golang"},
    # .NET ecosystem — all variants map to each other
    "c#": {"csharp"},       # c# ≠ .net: they're related but not synonyms
    "csharp": {"c#"},
    ".net": {"dotnet", ".net6", ".net core", "asp.net"},
    ".net6": {".net", "dotnet"},
    ".net core": {".net", "dotnet"},
    "asp.net": {".net", "asp.net core"},
    "asp.net core": {"asp.net", ".net"},
    "dotnet": {".net", ".net6", "asp.net"},
    "machine learning": {"ml", "deep learning"},
    "deep learning": {"dl", "machine learning"},
    "sql": {"mysql", "postgresql", "postgres", "sql server"},
}

# Related skills that grant PARTIAL credit (not full match)
SKILL_RELATIVES = {
    "react": {"vue", "angular", "svelte"},
    "vue": {"react", "angular", "svelte"},
    "angular": {"react", "vue", "svelte"},
    "django": {"flask", "fastapi"},
    "flask": {"django", "fastapi"},
    "fastapi": {"django", "flask"},
    "spring": {"spring boot", "springboot"},
    "spring boot": {"spring", "springboot"},
    "mysql": {"postgresql", "postgres", "mariadb"},
    "postgresql": {"mysql", "mariadb"},
    "mongodb": {"couchdb", "firebase", "firestore"},
    "aws": {"azure", "gcp", "google cloud"},
    "azure": {"aws", "gcp", "google cloud"},
    "gcp": {"aws", "azure"},
    "docker": {"kubernetes", "k8s"},
    "kubernetes": {"docker"},
    "jenkins": {"gitlab ci", "github actions", "circleci"},
    "gitlab ci": {"jenkins", "github actions", "circleci"},
    "github actions": {"jenkins", "gitlab ci", "circleci"},
    "pytest": {"unittest", "jest", "mocha"},
    "jest": {"vitest", "mocha", "pytest"},
    "cypress": {"selenium", "playwright", "puppeteer"},
    "selenium": {"cypress", "playwright"},
    "tensorflow": {"pytorch", "keras"},
    "pytorch": {"tensorflow", "keras"},
    "pandas": {"numpy", "scipy"},
}


@dataclass
class ExtractedSkill:
    """Représente une compétence extraite avec son contexte."""
    name: str
    original_text: str
    category: str
    category_label: str
    confidence: float
    is_required: bool = False
    is_preferred: bool = False
    level: Optional[str] = None
    tier: str = TIER_CRITICAL  # critical, important, noise

    def to_dict(self) -> dict:
        return {
            "name": self.name, "original_text": self.original_text,
            "category": self.category, "category_label": self.category_label,
            "confidence": round(self.confidence, 2),
            "is_required": self.is_required, "is_preferred": self.is_preferred,
            "level": self.level,
            "tier": self.tier,
        }


class SkillExtractor:
    FUZZY_THRESHOLD = 82

    def __init__(self, taxonomy_path: Optional[str] = None):
        if taxonomy_path is None:
            taxonomy_path = str(Path(__file__).parent.parent / "data" / "skills_taxonomy.json")
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            self.taxonomy = json.load(f)
        
        self._skill_index: Dict[str, Tuple[str, str]] = {}
        self._all_skills: List[str] = []
        for cat_key, cat_data in self.taxonomy["categories"].items():
            for skill in cat_data["skills"]:
                self._skill_index[skill.lower()] = (cat_key, cat_data["label"])
                self._all_skills.append(skill.lower())
                
        self.level_indicators = self.taxonomy.get("level_indicators", {})
        self.requirement_indicators = self.taxonomy.get("requirement_indicators", {})
        
        # Load NLP model safely
        try:
            self.nlp = spacy.load("fr_core_news_sm")
        except Exception:
            self.nlp = None

    def _classify_tier(self, skill_name: str, category: str) -> str:
        """
        Classify a skill into its importance tier.
        This is the KEY innovation — we don't treat "rigueur" the same as "Python".
        """
        # Check if it's a known noise phrase first (regardless of category)
        if skill_name.lower() in ALL_NOISE_PHRASES:
            return TIER_NOISE
        
        # Check by category
        if category in CRITICAL_CATEGORIES:
            return TIER_CRITICAL
        elif category in IMPORTANT_CATEGORIES:
            return TIER_IMPORTANT
        elif category in NOISE_CATEGORIES:
            return TIER_NOISE
        
        # Dynamic criteria default to IMPORTANT
        if category == "dynamic_criteria":
            # But check if it smells like noise
            if skill_name.lower() in ALL_NOISE_PHRASES:
                return TIER_NOISE
            return TIER_IMPORTANT
        
        return TIER_IMPORTANT

    def extract_skills(self, text: str, is_job_posting: bool = False) -> List[ExtractedSkill]:
        """Extrait les compétences reconnues dans la taxonomie."""
        text_lower = text.lower()
        found: Dict[str, ExtractedSkill] = {}

        # Phase 1: Exact taxonomy matching
        for skill_name, (category, label) in self._skill_index.items():
            if self._find_skill_in_text(skill_name, text_lower):
                if skill_name not in found:
                    conf = 1.0 if len(skill_name) > 2 else 0.85
                    tier = self._classify_tier(skill_name, category)
                    found[skill_name] = ExtractedSkill(
                        name=skill_name, original_text=skill_name,
                        category=category, category_label=label, confidence=conf,
                        tier=tier,
                    )

        # Phase 2: Fuzzy matching
        phrases = self._extract_candidate_phrases(text_lower)
        for phrase in phrases:
            if phrase in found or len(phrase) < 2:
                continue
            match = process.extractOne(phrase, self._all_skills, scorer=fuzz.ratio, score_cutoff=self.FUZZY_THRESHOLD)
            if match:
                matched_skill, score, _ = match
                if matched_skill not in found:
                    category, label = self._skill_index[matched_skill]
                    tier = self._classify_tier(matched_skill, category)
                    found[matched_skill] = ExtractedSkill(
                        name=matched_skill, original_text=phrase,
                        category=category, category_label=label, confidence=score / 100.0,
                        tier=tier,
                    )

        # Phase 3: Context enrichment
        results = list(found.values())
        for skill in results:
            skill.level = self._detect_level(text_lower, skill.name)
            if is_job_posting:
                req = self._detect_requirement(text_lower, skill.name)
                skill.is_required = req == "required" or req is None
                skill.is_preferred = req == "preferred"
                # Preferred soft skills are definitely noise
                if skill.is_preferred and skill.tier == TIER_NOISE:
                    skill.tier = TIER_NOISE

        results.sort(key=lambda s: (
            0 if s.tier == TIER_CRITICAL else 1 if s.tier == TIER_IMPORTANT else 2,
            -s.confidence
        ))
        return results

    def extract_dynamic_criteria(self, text: str, taxonomy_skills: List[ExtractedSkill]) -> List[ExtractedSkill]:
        """
        Extrait des mots-clés spécifiques au poste qui ne sont pas dans la taxonomie
        en utilisant le NLP (Nouns & Proper Nouns).
        Filters out noise phrases aggressively.
        """
        if not self.nlp:
            return []
            
        doc = self.nlp(text)
        
        # Obtenir les compétences déjà trouvées pour les exclure
        existing_names = {s.name for s in taxonomy_skills}
        
        dynamic_found = {}
        # Rechercher des entités ou noms propres pertinents (souvent des outils/techniques)
        for chunk in doc.noun_chunks:
            # Nettoyer
            chunk_text = chunk.text.lower().strip()
            
            # Enlever les puces, numéros, tirets, parenthèses et caractères spéciaux au début
            chunk_text = re.sub(r'^[\s\-\*\•\d\,\/\(\)]+', '', chunk_text)
            # Enlever les caractères spéciaux à la fin (garder + et #)
            chunk_text = re.sub(r'[\s\-\*\•\,\/\(\)]+$', '', chunk_text).strip()
            
            # Enlever les déterminants (le, la, un, des, etc.) au début
            chunk_text = re.sub(r'^(le |la |les |un |une |des |d\'|l\')', '', chunk_text)
            
            # Filtre de base
            if len(chunk_text) < 3 or len(chunk_text) > 30:
                continue
                
            # Exclure si déjà présent dans la taxonomie ou déjà trouvé
            if chunk_text in existing_names or chunk_text in self._skill_index:
                continue
            
            # Exclure les pronoms, prépositions, verbes et mots de liaison courants
            pronouns_preps = {
                "vous", "nous", "elle", "elles", "leur", "leurs", "dont", "avec", "pour", "dans", 
                "sans", "très", "tout", "tous", "toute", "toutes", "mais", "donc", "compte", 
                "plus", "moins", "comme", "chez", "sous", "vers", "pour", "notre", "votre", 
                "votre/notre", "leurs", "ceux", "celles", "celui", "celle", "ceci", "cela", "cette"
            }
            if chunk_text in pronouns_preps:
                continue

            # ── SMART FILTER: Skip generic filler phrases ──
            if chunk_text in ALL_NOISE_PHRASES:
                continue
            # Skip if it's a substring of a noise phrase
            if any(chunk_text in noise for noise in ALL_NOISE_PHRASES):
                continue
            # Skip very generic words (massively expanded to kill job-posting boilerplate)
            generic_words = {
                # Job posting structure words
                "poste", "candidat", "candidate", "profil", "mission", "missions",
                "entreprise", "société", "équipe", "projet", "projets", "expérience",
                "année", "années", "ans", "mois", "environnement", "contexte",
                "sein", "cadre", "niveau", "connaissance", "connaissances",
                "compétence", "compétences", "formation", "diplôme", "bac",
                "master", "licence", "ingénieur", "développeur", "technicien",
                "responsable", "manager", "directeur", "chef", "lead",
                # Generic action words from job description body
                "qualité", "amélioration", "optimisation", "mise en place",
                "mise en œuvre", "participation", "contribution", "rédaction",
                "suivi", "gestion", "pilotage", "coordination", "conception",
                "réalisation", "développement", "maintenance", "support",
                "assistance", "collaboration", "travail", "activité", "activités",
                "tâche", "tâches", "fonction", "rôle", "responsabilité",
                # Contract/location boilerplate
                "avantage", "avantages", "salaire", "rémunération", "contrat",
                "cdi", "cdd", "stage", "alternance", "freelance",
                "lieu", "localisation", "élétravail", "remote", "hybride",
                "temps", "plein", "partiel", "horaires", "jours", "h/f", "h-f",
                # Very common French words that appear everywhere
                "analyse", "veille", "matrîse", "maitrise", "maîtrise",
                "cœur", "coeur", "emploi", "type", "date", "mots", "clés",
                "description", "présentation", "exigences", "profil",
                "résumé", "curriculum", "vitae",
                # Company name fragments / location fragments
                "cisa", "informatique", "sousse", "ariana", "tunis", "tunisie",
                "novation", "city", "technopole", "filiale",
                # Technical but too vague to be a skill
                "progiciels", "logiciel", "logiciels", "système", "systèmes",
                "application", "applications", "plateforme", "outils", "outil",
                "architecture", "solution", "solutions", "module", "modules",
                "service", "services", "interface", "interfaces",
                # Conformance / legal / HR boilerplate
                "conformité", "conformité", "médiation", "régulation", "norme",
                "normes", "procédure", "procédures", "processus", "audit",
                "réglementation", "réglementaire",
                "recrutement", "ressources", "humaines", "rh",
                # Education words
                "dess", "dea", "dess", "bac+5", "grandes ecoles", "grandes écoles",
                "dess", "licence", "doctorat",
            }
            if chunk_text in generic_words:
                continue
            # Skip if the chunk is a SINGLE word (single-word dynamic criteria = always noise)
            # Only multi-word phrases can be genuine job-specific criteria not in the taxonomy
            words_in_chunk = chunk_text.split()
            if len(words_in_chunk) < 2:
                continue
            # Skip if all words are < 3 chars
            if all(len(w) < 3 for w in words_in_chunk):
                continue
            # Skip if any word is from the generic list
            if any(w in generic_words for w in words_in_chunk):
                continue
                
            # Count frequency
            if chunk_text not in dynamic_found:
                dynamic_found[chunk_text] = 0
            dynamic_found[chunk_text] += 1

        # Require at least 3 occurrences — single-mention nouns are noise
        sorted_dynamic = sorted(
            [k for k, v in dynamic_found.items() if v >= 3],
            key=lambda k: dynamic_found[k], reverse=True
        )
        
        # Limit to top 8 precise multi-word criteria
        best_dynamic = sorted_dynamic[:8]
        
        results = []
        for kw in best_dynamic:
            tier = self._classify_tier(kw, "dynamic_criteria")
            results.append(ExtractedSkill(
                name=kw, original_text=kw,
                category="dynamic_criteria", category_label="Critères Spécifiques à l'Offre",
                confidence=0.8, is_required=True,
                tier=tier,
            ))
            
        return results

    def find_specific_skills(self, text: str, specific_skills: List[ExtractedSkill]) -> List[ExtractedSkill]:
        """Recherche une liste de compétences spécifiques dans un texte (ex: recherche des critères dynamiques de l'offre dans le CV)."""
        text_lower = text.lower()
        found = []
        
        for skill in specific_skills:
            if self._find_skill_in_text(skill.name, text_lower):
                found.append(ExtractedSkill(
                    name=skill.name, original_text=skill.name,
                    category=skill.category, category_label=skill.category_label,
                    confidence=skill.confidence,
                    tier=skill.tier,
                ))
            else:
                # Fuzzy fallback
                match = process.extractOne(skill.name, text_lower.split(), scorer=fuzz.partial_ratio, score_cutoff=90)
                if match:
                    found.append(ExtractedSkill(
                        name=skill.name, original_text=skill.name,
                        category=skill.category, category_label=skill.category_label,
                        confidence=0.75,
                        tier=skill.tier,
                    ))
                    
        return found

    def find_synonyms_and_relatives(
        self, cv_skill_names: Set[str], job_skill_names: Set[str]
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        For each missing job skill, check if the CV has a synonym (= full match)
        or a related skill (= partial credit).
        
        Returns:
            synonym_matches: {job_skill: cv_skill} — should count as match
            relative_matches: {job_skill: cv_skill} — should count as partial
        """
        missing = job_skill_names - cv_skill_names
        synonym_matches = {}
        relative_matches = {}
        
        for job_skill in missing:
            # Check synonyms (= equivalent, full credit)
            syns = SKILL_SYNONYMS.get(job_skill, set())
            for syn in syns:
                if syn in cv_skill_names:
                    synonym_matches[job_skill] = syn
                    break
            
            if job_skill in synonym_matches:
                continue
            
            # Check relatives (= similar, partial credit)
            rels = SKILL_RELATIVES.get(job_skill, set())
            for rel in rels:
                if rel in cv_skill_names:
                    relative_matches[job_skill] = rel
                    break
        
        return synonym_matches, relative_matches

    def _find_skill_in_text(self, skill: str, text: str) -> bool:
        skill_lower = skill.lower()
        text_lower = text.lower()
        
        # Special case for platforms/URLs like github.com/user, gitlab.com, etc.
        if skill_lower in ("github", "gitlab", "bitbucket"):
            return skill_lower in text_lower or f"{skill_lower}.com" in text_lower

        # ── Ambiguous common-word skills: require explicit CSS context ──
        # "less" is a normal English/French word. Only match it as the LESS
        # CSS preprocessor when clearly used in a CSS/style context.
        if skill_lower == "less":
            css_patterns = [
                r'less\.js', r'lesscss', r'less\s+css', r'sass.*less', r'less.*sass',
                r'less.*scss', r'scss.*less', r'preprocesseur.*less', r'less.*preprocesseur',
            ]
            return any(re.search(p, text_lower) for p in css_patterns)

        # ── Skills with special chars (+, #, .): plain substring search ──
        # MUST come before the len<=2 check: c# is len=2 but requires substring
        # matching, not word-boundary matching (c# fails because # is non-word).
        if any(ch in skill_lower for ch in ['+', '#', '.']):
            return skill_lower in text_lower

        # ── Short skills (1–2 chars): protect against false subword matches ──
        if len(skill_lower) <= 2:
            if skill_lower == 'c':
                # Must not match inside c#, c++, c.something
                return bool(re.search(r'(?<![a-z])c(?![#\+\.\w])', text_lower))
            if skill_lower == 'r':
                # R programming language
                return bool(re.search(r'(?<![a-z])r(?![\w])', text_lower))
            patterns = [rf'\b{re.escape(skill_lower)}\b', rf'langage\s+{re.escape(skill_lower)}\b']
            return any(re.search(p, text_lower) for p in patterns)

        return bool(re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower))

    def _extract_candidate_phrases(self, text: str) -> Set[str]:
        clean = re.sub(r'[^\w\s\-\+\#\./]', ' ', text)
        words = clean.split()
        candidates = set()
        for i, w in enumerate(words):
            if len(w) >= 2:
                candidates.add(w)
            if i + 1 < len(words):
                candidates.add(f"{w} {words[i+1]}")
            if i + 2 < len(words):
                candidates.add(f"{w} {words[i+1]} {words[i+2]}")
        return candidates

    def _detect_level(self, text: str, skill_name: str) -> Optional[str]:
        pos = text.find(skill_name)
        if pos == -1:
            return None
        ctx = text[max(0, pos - 100):min(len(text), pos + len(skill_name) + 100)]
        for level, indicators in self.level_indicators.items():
            for ind in indicators:
                if ind.lower() in ctx:
                    return level
        return None

    def _detect_requirement(self, text: str, skill_name: str) -> Optional[str]:
        pos = text.find(skill_name)
        if pos == -1:
            return None
        ctx = text[max(0, pos - 200):min(len(text), pos + len(skill_name) + 200)]
        for ind in self.requirement_indicators.get("preferred", []):
            if ind.lower() in ctx:
                return "preferred"
        for ind in self.requirement_indicators.get("required", []):
            if ind.lower() in ctx:
                return "required"
        return None
