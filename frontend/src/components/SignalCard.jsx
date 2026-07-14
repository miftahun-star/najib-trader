import { Link } from 'react-router-dom'
import ScoreGauge from './ScoreGauge'
import TimeframeBadge from './TimeframeBadge'

export default function SignalCard({ data }) {
  if (!data) return null

  const { ticker, market, timeframes = {}, yearly_trend = {} } = data
  const daily = timeframes.daily || {}
  const signal = daily.signal || 'HOLD'
  const score = daily.score || 50
  const tl = daily.trade_levels || {}
  const price = daily.indicators?.price

  const signalClass = signal.toLowerCase()

  return (
    <div className={`glass-card fade-in`} style={{ padding: 20, position: 'relative', overflow: 'hidden' }}>
      {/* Glow effect for active signals */}
      {(signal === 'BOTTOM' || signal === 'PEAK') && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: signal === 'BOTTOM'
            ? 'linear-gradient(90deg, transparent, var(--green), transparent)'
            : 'linear-gradient(90deg, transparent, var(--red), transparent)',
        }} />
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <Link
            to={`/ticker/${encodeURIComponent(ticker)}`}
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: '1rem',
              color: 'var(--text-primary)',
              textDecoration: 'none',
            }}
          >
            {ticker}
          </Link>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
            {market}
          </div>
        </div>
        <ScoreGauge score={score} size={56} />
      </div>

      {/* Signal badge */}
      <div style={{ marginBottom: 12 }}>
        <span className={`signal-badge ${signalClass}`}>
          <span className="dot" />
          {signal}
        </span>
      </div>

      {/* Price */}
      {price && (
        <div style={{ marginBottom: 12 }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Price </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.95rem' }}>
            {typeof price === 'number' ? price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : price}
          </span>
        </div>
      )}

      {/* Trade levels for actionable signals */}
      {(signal === 'BOTTOM' || signal === 'PEAK') && tl.entry && (
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          borderRadius: 'var(--radius-sm)',
          padding: '10px 12px',
          marginBottom: 12,
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 16px', fontSize: '0.72rem' }}>
            <Level label="Entry" value={tl.entry} />
            <Level label="Stop Loss" value={tl.stop_loss} color="var(--red)" />
            <Level label="TP1" value={tl.tp1} color="var(--green)" />
            <Level label="TP2" value={tl.tp2} color="var(--green)" />
            <Level label="TP3" value={tl.tp3} color="var(--green)" />
            <Level label="R:R" value={tl.rr_ratio} />
          </div>
        </div>
      )}

      {/* Timeframe badges */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {Object.keys(timeframes).map(tf => (
          <div key={tf} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <TimeframeBadge timeframe={tf} />
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 600,
              color: getSignalColor(timeframes[tf]?.signal),
            }}>
              {timeframes[tf]?.signal || '—'}
            </span>
          </div>
        ))}
      </div>

      {/* Yearly trend */}
      {yearly_trend.bias && yearly_trend.bias !== 'neutral' && (
        <div style={{
          marginTop: 8,
          fontSize: '0.65rem',
          color: 'var(--text-muted)',
        }}>
          Yearly: {yearly_trend.structure || yearly_trend.bias}
        </div>
      )}
    </div>
  )
}

function Level({ label, value, color }) {
  if (value == null) return null
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: color || 'var(--text-primary)' }}>
        {typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}
      </span>
    </div>
  )
}

function getSignalColor(signal) {
  switch (signal) {
    case 'BOTTOM': return 'var(--green)'
    case 'PEAK': return 'var(--red)'
    case 'WATCH': return 'var(--amber)'
    default: return 'var(--text-muted)'
  }
}
