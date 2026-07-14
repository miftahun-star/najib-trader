export default function TimeframeBadge({ timeframe }) {
  const labels = { daily: 'D', weekly: 'W', monthly: 'M', yearly: 'Y' }
  const colors = {
    daily: 'var(--blue)',
    weekly: 'var(--green)',
    monthly: 'var(--amber)',
    yearly: 'var(--slate)',
  }
  const label = labels[timeframe] || timeframe
  const color = colors[timeframe] || 'var(--text-muted)'

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 24,
      height: 24,
      borderRadius: 6,
      fontSize: '0.65rem',
      fontWeight: 700,
      fontFamily: 'var(--font-mono)',
      color: color,
      background: `color-mix(in srgb, ${color} 15%, transparent)`,
      border: `1px solid color-mix(in srgb, ${color} 25%, transparent)`,
    }}>
      {label}
    </span>
  )
}
