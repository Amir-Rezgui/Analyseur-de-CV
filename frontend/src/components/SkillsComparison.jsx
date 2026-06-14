// SVG micro-icons for skill tags
const CheckSmall = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20,6 9,17 4,12" />
  </svg>
)

const XSmall = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
)

const PlusSmall = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
)

const SynonymIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 7h12M8 12h12M8 17h12" />
    <circle cx="4" cy="7" r="1" fill="currentColor" />
    <circle cx="4" cy="12" r="1" fill="currentColor" />
    <circle cx="4" cy="17" r="1" fill="currentColor" />
  </svg>
)

const RelatedIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 5v14M5 12h14" />
  </svg>
)

function SkillsComparison({ categoryScores }) {
  const getRatioBadgeClass = (ratio) => {
    if (ratio >= 0.8) return 'excellent'
    if (ratio >= 0.6) return 'good'
    if (ratio >= 0.4) return 'medium'
    return 'poor'
  }

  const getBarColor = (ratio) => {
    if (ratio >= 0.8) return 'var(--success)'
    if (ratio >= 0.6) return 'var(--info)'
    if (ratio >= 0.4) return 'var(--warning)'
    return 'var(--danger)'
  }

  const getTierLabel = (tier) => {
    switch (tier) {
      case 'critical': return 'Critique'
      case 'important': return 'Important'
      case 'noise': return 'Secondaire'
      default: return ''
    }
  }

  const getTierClass = (tier) => {
    switch (tier) {
      case 'critical': return 'tier-critical'
      case 'important': return 'tier-important'
      case 'noise': return 'tier-noise'
      default: return ''
    }
  }

  if (!categoryScores || categoryScores.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
        Aucune catégorie à afficher.
      </div>
    )
  }

  // Separate by tier for display
  const criticalCats = categoryScores.filter(cs => cs.tier === 'critical')
  const importantCats = categoryScores.filter(cs => cs.tier === 'important')
  const noiseCats = categoryScores.filter(cs => cs.tier === 'noise')

  const renderCategory = (cs, index) => (
    <div
      key={cs.category}
      className={`category-card ${cs.tier === 'noise' ? 'category-card-noise' : ''}`}
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <div className="category-header">
        <div className="category-name-group">
          <span className="category-name">{cs.category_label}</span>
          <span className={`tier-badge ${getTierClass(cs.tier)}`}>
            {getTierLabel(cs.tier)}
          </span>
        </div>
        <span className={`category-badge ${getRatioBadgeClass(cs.match_ratio)}`}>
          {(cs.match_ratio * 100).toFixed(0)}%
        </span>
      </div>

      <div className="category-progress">
        <div
          className="category-progress-fill"
          style={{
            width: `${cs.match_ratio * 100}%`,
            background: getBarColor(cs.match_ratio),
            transitionDelay: `${index * 0.05}s`,
          }}
        />
      </div>

      <div className="category-skills">
        {/* Exact matches */}
        {cs.matched_skills.map((skill) => (
          <span key={skill} className="skill-tag matched">
            <CheckSmall /> {skill}
          </span>
        ))}
        
        {/* Synonym matches */}
        {cs.synonym_skills && cs.synonym_skills.map((syn) => (
          <span key={syn.job} className="skill-tag synonym" title={`Équivalent: le CV contient "${syn.cv}"`}>
            <SynonymIcon /> {syn.job} <span className="skill-via">≈ {syn.cv}</span>
          </span>
        ))}
        
        {/* Compétences proches (related) : orange */}
        {cs.related_skills && cs.related_skills.map((rel) => (
          <span key={rel.job} className="skill-tag related" title={`Compétence proche: le candidat connaît "${rel.cv}"`}>
            <RelatedIcon /> {rel.job} <span className="skill-via">↔ {rel.cv}</span>
          </span>
        ))}
        
        {/* Missing skills */}
        {cs.missing_skills.map((skill) => (
          <span key={skill} className="skill-tag missing">
            <XSmall /> {skill}
          </span>
        ))}
        
        {/* Extra skills from CV */}
        {cs.extra_skills.slice(0, 3).map((skill) => (
          <span key={skill} className="skill-tag extra">
            <PlusSmall /> {skill}
          </span>
        ))}
      </div>
    </div>
  )

  return (
    <div className="categories-container">
      {criticalCats.length > 0 && (
        <div className="tier-section">
          <div className="tier-section-header">
            <span className="tier-section-dot tier-dot-critical" />
            <span className="tier-section-title">Compétences Critiques</span>
            <span className="tier-section-desc">— Ce qui compte vraiment pour le poste</span>
          </div>
          <div className="categories-grid">
            {criticalCats.map((cs, i) => renderCategory(cs, i))}
          </div>
        </div>
      )}
      
      {importantCats.length > 0 && (
        <div className="tier-section">
          <div className="tier-section-header">
            <span className="tier-section-dot tier-dot-important" />
            <span className="tier-section-title">Compétences Importantes</span>
            <span className="tier-section-desc">— Méthodologies, certifications, domaine</span>
          </div>
          <div className="categories-grid">
            {importantCats.map((cs, i) => renderCategory(cs, i + criticalCats.length))}
          </div>
        </div>
      )}
      
      {noiseCats.length > 0 && (
        <div className="tier-section tier-section-noise">
          <div className="tier-section-header">
            <span className="tier-section-dot tier-dot-noise" />
            <span className="tier-section-title">Soft Skills & Qualités Génériques</span>
            <span className="tier-section-desc">— Faible impact sur le score (c'est normal)</span>
          </div>
          <div className="categories-grid">
            {noiseCats.map((cs, i) => renderCategory(cs, i + criticalCats.length + importantCats.length))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SkillsComparison
