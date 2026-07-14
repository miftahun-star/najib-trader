export default function ScoreGauge({ score = 50, size = 80 }) {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference

  const getColor = (s) => {
    if (s >= 70) return 'var(--green)'
    if (s <= 30) return 'var(--red)'
    if (s >= 40 && s <= 60) return 'var(--slate)'
    return 'var(--amber)'
  }

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="4"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor(score)}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      <div style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          fontSize: size * 0.25,
          color: getColor(score),
          lineHeight: 1,
        }}>
          {Math.round(score)}
        </span>
      </div>
    </div>
  )
}
