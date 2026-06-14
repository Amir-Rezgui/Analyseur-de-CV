import ScoreGauge from './ScoreGauge'
import SkillsComparison from './SkillsComparison'

// SVG Icons
const ArrowLeftIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12" />
    <polyline points="12,19 5,12 12,5" />
  </svg>
)

const DownloadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7,10 12,15 17,10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

const BarChartIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
)

const CheckIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20,6 9,17 4,12" />
  </svg>
)

const AlertTriangleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
)

const LightbulbIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="9" y1="18" x2="15" y2="18" />
    <line x1="10" y1="22" x2="14" y2="22" />
    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
  </svg>
)

const BrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a4 4 0 0 1 4 4 4 4 0 0 1-1.5 3.13A4 4 0 0 1 16 13a4 4 0 0 1-4 4 4 4 0 0 1-4-4 4 4 0 0 1 1.5-3.13A4 4 0 0 1 8 6a4 4 0 0 1 4-4z" />
    <path d="M12 17v5" />
  </svg>
)

function ResultsDashboard({ results, onReset, apiBase }) {
  const { scoring, cv_skills_count, job_skills_count, session_id } = results
  const {
    overall_score,
    classification,
    category_scores,
    total_matched,
    total_required,
    total_extra,
    total_synonyms,
    total_related,
    strengths,
    weaknesses,
    recommendations,
    noise_skills_ignored,
  } = scoring

  const getScoreColor = (score) => {
    if (score >= 82) return 'var(--success)'
    if (score >= 65) return 'var(--info)'
    if (score >= 45) return 'var(--warning)'
    return 'var(--danger)'
  }

  // Count truly critical skills
  const criticalTotal = category_scores
    .filter(cs => cs.tier === 'critical')
    .reduce((sum, cs) => sum + cs.required_count, 0)
  const criticalMatched = category_scores
    .filter(cs => cs.tier === 'critical')
    .reduce((sum, cs) => sum + cs.match_count, 0)

  // Forces Chrome to save to Downloads instead of opening a preview tab.
  // Using fetch + blob + programmatic click is the only reliable cross-browser method.
  const handleDownload = async (type) => {
    try {
      const url = `${apiBase}/api/report/${session_id}/rapport.${type}`
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Server returned ${response.status}`)
      const blob = await response.blob()
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `rapport_cv_match.${type}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(link.href)
    } catch (err) {
      alert("Erreur lors du téléchargement. Relancez l'analyse et réessayez.")
    }
  }

  return (
    <div className="results-section">
      {/* Header */}
      <div className="results-header">
        <h2>Résultats de l'Analyse</h2>
        <button className="back-btn" onClick={onReset}>
          <ArrowLeftIcon />
          Nouvelle Analyse
        </button>
      </div>

      {/* Score Card */}
      <div className="score-card">
        <div className="score-gauge-container">
          <ScoreGauge score={overall_score} color={getScoreColor(overall_score)} />
        </div>
        <div className="score-details">
          <div
            className="score-classification"
            style={{ color: getScoreColor(overall_score) }}
          >
            <span
              className="score-classification-dot"
              style={{ background: getScoreColor(overall_score) }}
            />
            {classification}
          </div>
          <p className="score-summary">
            Le CV correspond à <strong>{overall_score.toFixed(1)}%</strong> des
            exigences <em>réelles</em> du poste.
            {noise_skills_ignored && noise_skills_ignored.length > 0 && (
              <span className="noise-note">
                {' '}Les qualités génériques (soft skills) ont un impact minimal sur ce score.
              </span>
            )}
          </p>

          <div className="score-stats">
            <div className="score-stat">
              <span className="score-stat-value" style={{ color: 'var(--success)' }}>
                {total_matched}
              </span>
              <span className="score-stat-label">Matchées</span>
            </div>
            <div className="score-stat">
              <span className="score-stat-value" style={{ color: 'var(--danger)' }}>
                {total_required - total_matched - (total_related || 0)}
              </span>
              <span className="score-stat-label">Manquantes</span>
            </div>
            {total_synonyms > 0 && (
              <div className="score-stat">
                <span className="score-stat-value" style={{ color: 'var(--info)' }}>
                  {total_synonyms}
                </span>
                <span className="score-stat-label">Synonymes</span>
              </div>
            )}
            {total_related > 0 && (
              <div className="score-stat">
                <span className="score-stat-value" style={{ color: 'var(--warning)' }}>
                  {total_related}
                </span>
                <span className="score-stat-label">Proches</span>
              </div>
            )}
            <div className="score-stat">
              <span className="score-stat-value" style={{ color: 'var(--info)' }}>
                {criticalMatched}/{criticalTotal}
              </span>
              <span className="score-stat-label">Critiques</span>
            </div>
          </div>

          {/* Download Buttons — use programmatic fetch+blob to force Downloads folder */}
          <div className="download-btns">
            <button
              className="download-btn pdf"
              onClick={() => handleDownload('pdf')}
            >
              <DownloadIcon /> Rapport PDF
            </button>
            <button
              className="download-btn docx"
              onClick={() => handleDownload('docx')}
            >
              <DownloadIcon /> Rapport Word
            </button>
          </div>
        </div>
      </div>

      {/* Smart Matching Info Banner */}
      {(total_synonyms > 0 || total_related > 0) && (
        <div className="smart-match-banner">
          <BrainIcon />
          <div className="smart-match-text">
            <strong>Matching intelligent actif</strong>
            <span>
              {total_synonyms > 0 && `${total_synonyms} compétence(s) équivalente(s) détectée(s)`}
              {total_synonyms > 0 && total_related > 0 && ' · '}
              {total_related > 0 && `${total_related} compétence(s) proche(s) reconnue(s)`}
            </span>
          </div>
        </div>
      )}

      {/* Category Breakdown */}
      <h3 className="section-heading">
        <BarChartIcon />
        Détail par Catégorie
      </h3>
      <SkillsComparison categoryScores={category_scores} />

      {/* Insights */}
      <div className="insights-grid">
        {strengths.length > 0 && (
          <div className="insight-card" style={{ animationDelay: '0.1s' }}>
            <div className="insight-card-header">
              <span className="insight-card-icon strengths">
                <CheckIcon />
              </span>
              Points Forts
            </div>
            {strengths.map((s, i) => (
              <div key={i} className="insight-item">{s}</div>
            ))}
          </div>
        )}

        {weaknesses.length > 0 && (
          <div className="insight-card" style={{ animationDelay: '0.2s' }}>
            <div className="insight-card-header">
              <span className="insight-card-icon weaknesses">
                <AlertTriangleIcon />
              </span>
              Points à Améliorer
            </div>
            {weaknesses.map((w, i) => (
              <div key={i} className="insight-item">{w}</div>
            ))}
          </div>
        )}

        {recommendations.length > 0 && (
          <div className="insight-card" style={{ animationDelay: '0.3s' }}>
            <div className="insight-card-header">
              <span className="insight-card-icon recommendations">
                <LightbulbIcon />
              </span>
              Recommandations
            </div>
            {recommendations.map((r, i) => (
              <div key={i} className="insight-item">{r}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ResultsDashboard