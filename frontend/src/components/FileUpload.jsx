import { useState, useRef } from 'react'

const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17,8 12,3 7,8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
)

const FileIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14,2 14,8 20,8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
)

const BriefcaseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
  </svg>
)

const TextIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <line x1="17" y1="10" x2="3" y2="10" />
    <line x1="21" y1="6" x2="3" y2="6" />
    <line x1="21" y1="14" x2="3" y2="14" />
    <line x1="17" y1="18" x2="3" y2="18" />
  </svg>
)

const PdfIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14,2 14,8 20,8" />
  </svg>
)

const CheckCircleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22,4 12,14.01 9,11.01" />
  </svg>
)

const XIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
)

const ArrowRightIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" />
    <polyline points="12,5 19,12 12,19" />
  </svg>
)

const EXAMPLE_JD = `Ingénieur Full Stack — Python / React (H/F)

Nous recherchons un(e) Ingénieur Full Stack pour rejoindre notre équipe produit.

Missions :
- Développement de nouvelles fonctionnalités sur notre plateforme web (React, TypeScript)
- Conception et maintenance d'APIs RESTful en Python (FastAPI / Django)
- Gestion et optimisation de bases de données PostgreSQL et Redis
- Déploiement et monitoring sur AWS (EC2, Lambda, RDS, S3)
- Participation aux code reviews et à la culture DevOps (CI/CD, Docker, GitHub Actions)

Compétences requises :
- Python (3 ans min), JavaScript / TypeScript
- React.js, Node.js
- PostgreSQL, Redis
- Docker, Git
- AWS ou équivalent cloud
- Méthodologie Agile / Scrum

Compétences appréciées :
- GraphQL, Kubernetes
- Expérience en data engineering (dbt, Airflow)`

function FileUpload({ onAnalyze, loading }) {
  const [cvFile, setCvFile] = useState(null)
  const [jobFile, setJobFile] = useState(null)
  const [jobText, setJobText] = useState('')
  const [jobInputMode, setJobInputMode] = useState('text')
  const [draggingCv, setDraggingCv] = useState(false)
  const [draggingJob, setDraggingJob] = useState(false)

  const cvInputRef = useRef(null)
  const jobInputRef = useRef(null)

  const handleSubmit = () => {
    if (!cvFile) return
    if (jobInputMode === 'pdf' && !jobFile) return
    if (jobInputMode === 'text' && !jobText.trim()) return

    onAnalyze(
      cvFile,
      jobInputMode === 'pdf' ? jobFile : null,
      jobInputMode === 'text' ? jobText : null
    )
  }

  const handleDrop = (e, setter, setDragging) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') setter(file)
  }

  const canSubmit =
    cvFile &&
    ((jobInputMode === 'pdf' && jobFile) ||
      (jobInputMode === 'text' && jobText.trim().length > 20))

  return (
    <div className="upload-section">
      <div className="upload-hero">
        <h1>
          Évaluez la <span className="gradient-text">compatibilité</span>
          <br />
          du CV avec le poste
        </h1>
        <p>
          Importez le CV et la fiche de poste — l'IA extrait, compare et génère un rapport professionnel en quelques secondes.
        </p>
        <div className="hero-pills">
          <span className="hero-pill">
            <span className="hero-pill-dot" style={{ background: 'var(--accent)' }} />
            Extraction IA
          </span>
          <span className="hero-pill">
            <span className="hero-pill-dot" style={{ background: 'var(--info)' }} />
            Scoring multi-niveaux
          </span>
          <span className="hero-pill">
            <span className="hero-pill-dot" style={{ background: 'var(--teal)' }} />
            Rapport PDF &amp; Word
          </span>
        </div>
      </div>

      <div className="upload-grid">
        {/* CV Upload */}
        <div className="upload-card">
          <div className="upload-card-header">
            <div className="upload-card-icon cv">
              <FileIcon />
            </div>
            <div>
              <div className="upload-card-title">Le CV</div>
              <div className="upload-card-desc">Format PDF uniquement</div>
            </div>
          </div>

          <div
            className={`drop-zone ${draggingCv ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDraggingCv(true) }}
            onDragLeave={() => setDraggingCv(false)}
            onDrop={(e) => handleDrop(e, setCvFile, setDraggingCv)}
            onClick={() => cvInputRef.current?.click()}
          >
            <div className="drop-zone-icon">
              <UploadIcon />
            </div>
            <div className="drop-zone-text">
              Glissez le CV ici ou <span style={{ color: 'var(--accent)', fontWeight: 600 }}>cliquez pour parcourir</span>
            </div>
            <div className="drop-zone-hint">PDF · Max 10 Mo</div>
            <input
              ref={cvInputRef}
              type="file"
              accept=".pdf"
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => setCvFile(e.target.files[0])}
            />
          </div>

          {cvFile && (
            <div className="file-selected">
              <span className="file-selected-icon"><CheckCircleIcon /></span>
              <span className="file-selected-name">{cvFile.name}</span>
              <button className="file-selected-remove" onClick={() => setCvFile(null)}>
                <XIcon />
              </button>
            </div>
          )}
        </div>

        {/* Job Description */}
        <div className="upload-card">
          <div className="upload-card-header">
            <div className="upload-card-icon job">
              <BriefcaseIcon />
            </div>
            <div>
              <div className="upload-card-title">Fiche de Poste</div>
              <div className="upload-card-desc">PDF ou texte libre</div>
            </div>
          </div>

          <div className="input-toggle">
            <button
              className={`toggle-btn ${jobInputMode === 'text' ? 'active' : ''}`}
              onClick={() => setJobInputMode('text')}
            >
              <TextIcon /> Texte
            </button>
            <button
              className={`toggle-btn ${jobInputMode === 'pdf' ? 'active' : ''}`}
              onClick={() => setJobInputMode('pdf')}
            >
              <PdfIcon /> PDF
            </button>
          </div>

          {jobInputMode === 'pdf' ? (
            <>
              <div
                className={`drop-zone ${draggingJob ? 'dragging' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDraggingJob(true) }}
                onDragLeave={() => setDraggingJob(false)}
                onDrop={(e) => handleDrop(e, setJobFile, setDraggingJob)}
                onClick={() => jobInputRef.current?.click()}
              >
                <div className="drop-zone-icon"><UploadIcon /></div>
                <div className="drop-zone-text">Glissez la fiche de poste ici</div>
                <div className="drop-zone-hint">PDF · Max 10 Mo</div>
                <input
                  ref={jobInputRef}
                  type="file"
                  accept=".pdf"
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => setJobFile(e.target.files[0])}
                />
              </div>
              {jobFile && (
                <div className="file-selected">
                  <span className="file-selected-icon"><CheckCircleIcon /></span>
                  <span className="file-selected-name">{jobFile.name}</span>
                  <button className="file-selected-remove" onClick={() => setJobFile(null)}>
                    <XIcon />
                  </button>
                </div>
              )}
            </>
          ) : (
            <div style={{ position: 'relative' }}>
              <textarea
                className="job-textarea"
                placeholder="Collez la description du poste ici…"
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
              />
              {!jobText && (
                <button
                  onClick={() => setJobText(EXAMPLE_JD)}
                  style={{
                    position: 'absolute',
                    bottom: 10,
                    right: 10,
                    padding: '4px 10px',
                    background: 'var(--bg-glass)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-muted)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-sans)',
                    cursor: 'pointer',
                  }}
                >
                  Exemple
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <button
        className={`analyze-btn ${loading ? 'loading' : ''}`}
        onClick={handleSubmit}
        disabled={!canSubmit || loading}
        id="analyze-button"
      >
        {loading ? (
          <>
            <span className="loading-spinner"></span>
            Analyse en cours…
          </>
        ) : (
          <>
            Lancer l'analyse
            <ArrowRightIcon />
          </>
        )}
      </button>
    </div>
  )
}

export default FileUpload
