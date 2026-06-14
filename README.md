# CV Fit Analyzer

Un outil full-stack qui analyse la compatibilité entre un CV et une fiche de poste. Il extrait les compétences techniques vérifiables, calcule un score de matching pondéré via GPT-4o-mini, et génère un rapport téléchargeable en PDF et Word.

---

## Tester le projet rapidement

> La clé OpenAI vous a été envoyée en privé. Suivez ces 4 étapes dans l'ordre.

**Étape 1 — Clé API**

À la racine du projet :
```bash
cp .env.example .env
```
Ouvrez `.env` et remplacez :
```
OPENAI_API_KEY=la-clé-reçue-en-privé
```

**Étape 2 — Backend** (Terminal 1)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
uvicorn main:app --reload --port 8000
```

**Étape 3 — Frontend** (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

**Étape 4 — Ouvrir**

→ http://localhost:5173

> Sans clé OpenAI, l'app bascule automatiquement en mode fallback local — l'interface reste complète.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  React + Vite  →  http://localhost:5173                     │
│                                                             │
│  FileUpload.jsx        → drag-and-drop CV + JD              │
│  ResultsDashboard.jsx  → score, breakdown, téléchargement   │
│  ScoreGauge.jsx        → jauge circulaire SVG               │
│  SkillsComparison.jsx  → détail par catégorie               │
└──────────────────────────┬──────────────────────────────────┘
                           │  POST /api/analyze
                           │  (multipart: CV PDF + JD text/PDF)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│  FastAPI (Python)  →  http://localhost:8000                 │
│                                                             │
│  1. pdf_parser.py        → extrait le texte brut du PDF     │
│                                                             │
│  2. llm_extractor.py     → appelle GPT-4o-mini             │
│     CV  → { experience, projects, certifications,           │
│             skills, languages }                             │
│     JD  → { required, preferred, nice_to_have }            │
│     Les soft skills sont filtrés par le prompt LLM          │
│                                                             │
│  3. scorer.py            → matching pondéré                 │
│     required x1.5  preferred x1.0  nice_to_have x0.3       │
│     evidence: experience > projects > certifs > skills list │
│                                                             │
│  4. report_generator.py  → PDF (reportlab) + DOCX           │
│                            (python-docx)                    │
└─────────────────────────────────────────────────────────────┘
```

**Pourquoi ces choix techniques :**
- **FastAPI** sur Flask : support async natif, validation Pydantic, docs Swagger auto
- **LLM pour l'extraction** sur regex/spaCy : les CVs ont des formats trop variables — un LLM comprend le contexte ("led a team using Agile" → extrait: Agile, team management)
- **Fallback taxonomy** : si la clé OpenAI est absente, l'app continue avec un extracteur local — pas de crash

---

## Structure du projet

```
CV_match/
├── .env                          ← à créer (voir étape 1)
├── .env.example                  ← modèle fourni
├── backend/
│   ├── main.py                   ← FastAPI : routes + orchestration
│   ├── requirements.txt
│   └── core/
│       ├── llm_extractor.py      ← extraction GPT-4o-mini (primaire)
│       ├── skill_extractor.py    ← taxonomy + spaCy (fallback)
│       ├── scorer.py             ← moteur de scoring pondéré
│       ├── pdf_parser.py         ← extraction texte PDF
│       └── report_generator.py   ← génération PDF + Word
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── FileUpload.jsx
            ├── ResultsDashboard.jsx
            ├── ScoreGauge.jsx
            └── SkillsComparison.jsx
```

---

## Endpoints API

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/analyze` | POST | CV PDF + JD → résultat scoring complet |
| `/api/report/{id}/rapport.pdf` | GET | Télécharge le rapport PDF |
| `/api/report/{id}/rapport.docx` | GET | Télécharge le rapport Word |

Documentation interactive : http://localhost:8000/docs

---

## Problèmes fréquents

| Problème | Solution |
|---|---|
| `Failed to fetch` | Vérifier que le backend tourne sur le port 8000 |
| `LLM extraction unavailable` | Vérifier la clé dans `.env` — fallback automatique si absente |
| PDF illisible | Utiliser un PDF natif (pas un scan image) |
| Port 8000 déjà utilisé | Lancer avec `--port 8001` et changer `API_BASE` dans `App.jsx` |