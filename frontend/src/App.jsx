import { useState, useEffect, useRef } from 'react'
import './App.css'
import FileUpload from './components/FileUpload'
import ResultsDashboard from './components/ResultsDashboard'

// Après
const API_BASE = ''

const LOADING_STEPS = [
  { label: 'Extraction du contenu du CV…', duration: 2000 },
  { label: 'Analyse de la fiche de poste…', duration: 2500 },
  { label: 'Calcul du score de compatibilité…', duration: 2000 },
  { label: 'Génération du rapport…', duration: 1500 },
]

function LoadingOverlay() {
  const [stepIndex, setStepIndex] = useState(0)
  const [progress, setProgress] = useState(0)
  const timerRef = useRef(null)

  useEffect(() => {
    let elapsed = 0
    const totalDuration = LOADING_STEPS.reduce((s, st) => s + st.duration, 0)
    const tick = () => {
      elapsed += 100
      setProgress(Math.min(95, (elapsed / totalDuration) * 100))
      let cumulative = 0
      for (let i = 0; i < LOADING_STEPS.length; i++) {
        cumulative += LOADING_STEPS[i].duration
        if (elapsed < cumulative) { setStepIndex(i); break }
      }
    }
    timerRef.current = setInterval(tick, 100)
    return () => clearInterval(timerRef.current)
  }, [])

  return (
    <div className="loading-overlay">
      <div className="loading-card">
        <div className="loading-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
        </div>
        <div className="loading-title">Analyse en cours</div>
        <div className="loading-steps">
          {LOADING_STEPS.map((step, i) => (
            <div key={i} className={`loading-step ${i < stepIndex ? 'done' : i === stepIndex ? 'active' : 'pending'}`}>
              <span className="loading-step-dot" />
              <span>{step.label}</span>
            </div>
          ))}
        </div>
        <div className="loading-bar">
          <div className="loading-bar-inner" style={{ width: `${progress}%`, transition: 'width 0.1s linear' }} />
        </div>
        <div className="loading-progress-text">{Math.round(progress)}%</div>
      </div>
    </div>
  )
}

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAnalyze = async (cvFile, jobFile, jobText) => {
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('cv_file', cvFile)
      if (jobFile) formData.append('job_file', jobFile)
      else if (jobText) formData.append('job_text', jobText)

      const response = await fetch(`${API_BASE}/api/analyze`, { method: 'POST', body: formData })
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || "L'analyse a échoué")
      }
      setResults(await response.json())
    } catch (err) {
      setError(err.message || "Impossible de se connecter au serveur. Le backend tourne-t-il sur le port 8000 ?")
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => { setResults(null); setError(null) }

  return (
    <div className="app">
      <header className="header">
        <div className="header-brand" onClick={handleReset} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && handleReset()}>
          <div className="header-logo">CF</div>
          <div>
            <div className="header-title">CV Fit Analyzer</div>
            <div className="header-subtitle">Propulsé par GPT-4o-mini</div>
          </div>
        </div>
        <div className="header-right">
          <div className="header-status">
            <span className="header-status-dot" />
            Système actif
          </div>
          <div className="header-badge">v2.0</div>
        </div>
      </header>

      {loading && <LoadingOverlay />}

      <main className="main-content">
        {error && (
          <div className="error-banner" role="alert">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <strong>Échec de l'analyse</strong>
              <p>{error}</p>
            </div>
            <button className="error-dismiss" onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {!results ? (
          <FileUpload onAnalyze={handleAnalyze} loading={loading} />
        ) : (
          <ResultsDashboard results={results} onReset={handleReset} apiBase={API_BASE} />
        )}
      </main>

      <footer className="app-footer">
        CV Fit Analyzer — Évaluation de compatibilité propulsée par l'IA &nbsp;·&nbsp; Résultats générés automatiquement
      </footer>
    </div>
  )
}

export default App
