# Architecture — CV Fit Analyzer

> Documentation technique pour l'évaluation de l'architecture.

---

## 1. Répartition des Composants

| Composant | Responsabilité |
|---|---|
| `main.py` | Application FastAPI, CORS, routage, gestion des sessions, orchestration LLM/fallback |
| `llm_extractor.py` | Extraction via GPT-4o-mini avec sortie JSON structurée, logique de relance (retry), conception des prompts |
| `skill_extractor.py` | Extracteur de secours basé sur une taxonomie (plus de 500 compétences, correspondance approximative (fuzzy matching), classification par niveaux) |
| `scorer.py` | Notation pondérée par niveaux (tiers), correspondance des synonymes et des compétences proches, normalisation sigmoïde |
| `pdf_parser.py` | Extraction de texte avec `pdfplumber`, normalisation de l'encodage, gestion des mises en page multi-colonnes |
| `report_generator.py` | Génération de rapports PDF (reportlab) et Word (python-docx) à partir d'une sortie de notation unifiée |
| `skills_taxonomy.json` | Base de données de compétences catégorisées avec métadonnées de domaine/niveau |
| `FileUpload.jsx` | Téléversement du CV par glisser-déposer, basculement texte/PDF pour la fiche de poste |
| `ResultsDashboard.jsx` | Fiche de score, détail par catégorie, boutons de téléchargement, insights |
| `ScoreGauge.jsx` | Jauge de progression circulaire en SVG avec animation d'apparition |
| `SkillsComparison.jsx` | Affichage des compétences correspondantes/manquantes groupées par niveaux avec indicateurs de synonymes |

---

## 2. Flux de Données Complet

```
L'utilisateur téléverse le CV (PDF) + La fiche de poste
         │
         ▼
  [FastAPI] POST /api/analyze
  ┌─────────────────────────────────────┐
  │ 1. pdfplumber extrait le texte brut │
  │    des fichiers PDF téléversés      │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │ 2. LLMExtractor (GPT-4o-mini)       │
  │    ┌──────────────────────────────┐ │
  │    │ Prompt CV → JSON structuré   │ │
  │    │ Prompt Poste → Compétences   │ │
  │    └──────────────────────────────┘ │
  │    En cas d'échec → SkillExtractor  │
  │    (secours taxonomie + spaCy)      │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │ 3. Scorer.calculate_score()         │
  │    • Notation pondérée par niveaux   │
  │    • Synonymes (React=ReactJS)       │
  │    • Crédit partiel pour compétences │
  │      proches                         │
  │    • Normalisation sigmoïde          │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │ 4. ReportGenerator                  │
  │    • generate_pdf() → reportlab     │
  │    • generate_docx() → python-docx  │
  │    Les deux consomment le même      │
  │    ScoringResult                    │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  Réponse JSON → Interface React
  (score, catégories, compétences, URLs des rapports)
```

---

## 3. Pourquoi FastAPI plutôt que Flask/Django

- **Asynchrone par défaut** : les E/S de fichiers, les appels HTTP vers OpenAI et la génération de rapports s'exécutent sans bloquer la boucle d'événements.
- **Documentation OpenAPI automatique** : endpoint `/docs` généré à partir des annotations de type — aucun effort supplémentaire.
- **Sécurité des types via Pydantic** : `UploadFile`, `Form` et les modèles de réponse sont validés automatiquement.
- **Gestion native du multipart** : `python-multipart` s'intègre parfaitement à FastAPI pour les téléversements de fichiers.
- Flask nécessite des wrappers asynchrones manuels ; Django entraîne une surcharge ORM/template qui n'apporte aucune valeur ici.

---

## 4. Pourquoi un LLM pour l'extraction plutôt que regex/spaCy

Les CV et les fiches de poste présentent des formatages extrêmement variables. Un analyseur basé sur des règles échoue sur :
- `"Travail avec React (projets persos) et un peu de Vue"` → ignore les deux sans contexte.
- `"Maîtrise de l'écosystème Node.js"` → contexte français, non détecté par des expressions régulières anglaises.
- `"Expérience souhaitée : 2 ans minimum avec Python, idéalement Django"` → impossible de classer sans comprendre "souhaitée".

Un LLM extrait des compétences contextuelles :
- `"a dirigé une équipe en utilisant Agile"` → extrait correctement `["Agile", "Scrum"]`.
- `"rigueur et désir d'apprendre"` → correctement classé comme bruit (soft skills) et exclu.
- Support multilingue sans avoir à maintenir des ensembles parallèles d'expressions régulières.

**GPT-4o-mini plutôt que GPT-4o** : 10 fois moins cher, 3 fois plus rapide, la qualité est suffisante pour l'extraction structurée — le prompt restreint suffisamment la tâche pour que le modèle plus large n'apporte aucun bénéfice mesurable ici.

**Raisonnement du système de secours (fallback)** : L'extracteur taxonomique local s'exécute en ~30 ms sans dépendance réseau. Si OpenAI est indisponible (quota, réseau), le système se dégrade gracieusement au lieu de planter.

---

## 5. Algorithme de Notation

### Formule

```
Pour chaque catégorie C de niveau T requise par le poste :
  poids(C) = poids_de_base(C) × multiplicateur_niveau(T)
  
  crédit(C) = (
    |correspondance_exacte| × 1.0 +
    |correspondance_synonyme| × 0.9 +
    |correspondance_proche| × 0.4 +
    |manquante_souhaitée| × 0.3 +
    |manquante_requise| × 0.0
  ) / |compétences_du_poste_dans_C|

  score_pondéré(C) = crédit(C) × poids_normalisé(C)

score_brut = Σ score_pondéré(C)  [la somme des poids normalisés vaut 1.0]

score_final = normalisation_sigmoide(score_brut) × 100 + bonus_penalite
```

### Multiplicateurs de Niveaux (Tiers)

| Niveau | Multiplicateur | Exemples |
|---|---|---|
| CRITIQUE (CRITICAL) | 1.0 | Python, React, PostgreSQL, Docker |
| IMPORTANT (IMPORTANT) | 0.4 | Agile, langues parlées, certifications |
| BRUIT (NOISE) | 0.05 | "rigoureux", "esprit d'équipe", "curieux" |

### Pourquoi une normalisation sigmoïde ?

Les scores pondérés bruts se concentrent généralement autour de 0,3–0,6 pour la plupart des candidats réels. Une échelle linéaire donnerait 30–60 %, ce qui est perçu comme un "échec", même pour de bons candidats. La sigmoïde ajuste cela :
- 0,0 brut → ~15 % final (véritablement non qualifié)
- 0,5 brut → ~55 % final (correspondance partielle)
- 0,7 brut → ~72 % final (bonne correspondance)
- 0,9 brut → ~85 % final (excellente correspondance)

Cela produit des scores qui semblent bien calibrés plutôt que d'être inutilement punitifs.

### Système de Bonus/Pénalité

| Condition | Ajustement |
|---|---|
| >80% de correspondance sur les catégories CRITIQUES | +4 points |
| Exigences linguistiques totalement remplies | +2 points |
| Synonymes détectés | +1 par synonyme (max +3) |
| <20% de correspondance sur les catégories techniques clés | -8 points |
| <30% de correspondance sur les catégories techniques clés | -4 points |

### Gestion des Soft Skills (Savoir-être)

Les compétences non techniques (niveau BRUIT/NOISE) sont :
1. **Affichées** dans l'interface sous une section dédiée — pour des raisons de transparence.
2. **Pondérées à 5 %** du poids de leur catégorie — impact minime sur le score.
3. **Jamais mentionnées comme des lacunes** dans les recommandations.
4. **Non comptabilisées** dans le ratio des compétences critiques affiché aux utilisateurs.

Cela signifie qu'une offre d'emploi demandant "rigoureux, curieux, esprit d'équipe" ne fera pas chuter le score d'un candidat si ces traits ne figurent pas sur son CV. Les recruteurs ne vérifient pas réellement cela sur papier — l'outil non plus.

---

## 6. Génération de Rapports

Les rapports PDF et Word consomment la même sortie (la dataclass `ScoringResult`) provenant de l'évaluateur (scorer) :

```python
@dataclass
class ScoringResult:
    overall_score: float
    classification: str
    category_scores: List[CategoryScore]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
```

**Pourquoi reportlab pour le PDF** : Contrôle total sur la mise en page, styles personnalisés, aucune surcharge liée à la conversion HTML→PDF. Rendu précis des tableaux pour la matrice détaillée des compétences.

**Pourquoi python-docx pour Word** : Format `.docx` natif, sans dépendance à LibreOffice. Sortie cohérente sur toutes les plateformes. Les responsables du recrutement peuvent éditer et annoter le rapport.

**Aucune duplication** : `generate_pdf()` et `generate_docx()` appellent toutes deux la même fonction d'aide pour formater le détail des catégories — seule la couche de rendu diffère.

### Ton et Perspective
L'ensemble du système (interface utilisateur, insights, et rapports générés) est conçu avec une **perspective objective destinée aux recruteurs**.
- Le système évalue "le candidat" ou "le CV" à la 3ème personne.
- Les insights et recommandations sont formulés comme des évaluations professionnelles pour les managers (ex. : "Le candidat maîtrise X — une formation sur Y serait pertinente") plutôt que comme un feedback direct adressé au candidat ("Votre CV a des lacunes en Y").

---

## 7. Stratégie de Prompting LLM

### Conception du Prompt CV

Le prompt du CV exige un schéma JSON strict avec des champs typés. Cela empêche les hallucinations en restreignant l'espace de sortie :
- Le modèle ne peut pas inventer de compétences absentes du texte (le prompt se concentre sur l'extraction factuelle).
- `response_format={"type": "json_object"}` impose un JSON valide au niveau de l'API.
- `temperature=0.0` rend la sortie déterministe.

### Conception du Prompt Poste — Le Point Clé

Le prompt de la fiche de poste nomme explicitement des exemples de ce qu'il NE FAUT PAS extraire :
> "IGNORE ALL of the following — rigueur, autonomie, curiosité, team player, good communicator..."

Nommer explicitement le bruit donne de bien meilleurs résultats que de simplement dire "n'extraire que les hard skills". Les LLM réagissent mieux aux exemples d'exclusions qu'aux définitions abstraites d'inclusions.

### Logique de Relance (Retry)

En cas d'échec de l'analyse JSON (rare avec le mode `json_object` mais possible) :
1. Ajouter la réponse ayant échoué à l'historique de la conversation.
2. Relancer le prompt : "Votre réponse précédente n'était pas un JSON valide. Retournez uniquement un objet JSON valide."
3. Le modèle se corrige dans >95 % des cas dès la deuxième tentative.
4. Après 2 échecs, renvoyer `None` → déclencher le système de secours taxonomique.

---

## 8. Principaux Compromis Techniques

| Décision | Choix retenu | Alternative | Raison |
|---|---|---|---|
| Modèle LLM | GPT-4o-mini | GPT-4o | 10x moins cher, 3x plus rapide, qualité d'extraction équivalente |
| Extraction PDF | pdfplumber | PyPDF2 | Meilleure gestion des tableaux/colonnes, métadonnées de mise en page plus riches |
| Graphiques | Jauge SVG + CSS | Recharts/D3 | Aucun poids supplémentaire (bundle JS) pour un simple affichage de progression |
| CSS | Vanilla | Tailwind | Contrôle total, pas de compilation JIT, bundle plus léger |
| Fallback d'extraction | spaCy + taxonomie | Aucun | Aucun temps d'arrêt si le quota OpenAI est dépassé |
| Stockage session | Dictionnaire en mémoire | Redis/DB | Suffisant pour une démo sur serveur unique ; remplacer par Redis pour la production |
| Notation | Normalisation sigmoïde | Linéaire | Empêche les scores extrêmes, produit des pourcentages réalistes |
