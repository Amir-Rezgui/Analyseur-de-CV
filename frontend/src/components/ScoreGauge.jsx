function ScoreGauge({ score, color }) {
  const radius = 62
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="score-gauge">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle
          className="score-gauge-bg"
          cx="70"
          cy="70"
          r={radius}
        />
        <circle
          className="score-gauge-fill"
          cx="70"
          cy="70"
          r={radius}
          style={{
            stroke: color,
            strokeDasharray: circumference,
            strokeDashoffset: offset,
          }}
        />
      </svg>
      <div className="score-gauge-text">
        <span className="score-value" style={{ color }}>
          {score.toFixed(0)}%
        </span>
        <span className="score-label">Score</span>
      </div>
    </div>
  )
}

export default ScoreGauge
