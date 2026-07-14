import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../App'
import SignalCard from './SignalCard'

export default function Dashboard() {
  const { signals, backtest, loadTicker } = useData()
  const [tickerDetails, setTickerDetails] = useState({})
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!signals?.tickers) return
    async function loadAll() {
      const details = {}
      for (const t of signals.tickers) {
        const data = await loadTicker(t.ticker)
        if (data) details[t.ticker] = data
      }
      setTickerDetails(details)
      setLoaded(true)
    }
    loadAll()
  }, [signals])

  if (!signals) return null

  const tickers = signals.tickers || []
  const ihsgTickers = tickers.filter(t => t.market === 'IHSG')
  const usTickers = tickers.filter(t => t.market === 'US')

  const bottomCount = tickers.filter(t => t.signal === 'BOTTOM').length
  const peakCount = tickers.filter(t => t.signal === 'PEAK').length
  const winRate = backtest?.overall?.win_rate || 0
  const nTrades = backtest?.overall?.n_trades || 0

  return (
    <div>
      <h1 style={{
        fontSize: '1.5rem',
        fontWeight: 800,
        marginBottom: 4,
        background: 'linear-gradient(135deg, var(--text-primary), var(--text-secondary))',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}>
        Signal Dashboard
      </h1>
      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 24 }}>
        Last updated: {signals.last_updated || '—'}
      </p>

      {/* Summary stats */}
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <StatCard label="Total Signals" value={tickers.length} icon="📡" delay={0} />
        <StatCard label="Bottom (Buy)" value={bottomCount} icon="🟢" color="var(--green)" delay={1} />
        <StatCard label="Peak (Sell)" value={peakCount} icon="🔴" color="var(--red)" delay={2} />
        <StatCard
          label="Backtest Win Rate"
          value={nTrades > 0 ? `${winRate}%` : '—'}
          icon="📈"
          color="var(--blue)"
          subtitle={nTrades > 0 ? `n=${nTrades} trades` : 'No data yet'}
          delay={3}
        />
      </div>

      {/* IHSG section */}
      <div style={{ marginBottom: 32 }}>
        <h2 className="section-title">
          <span className="emoji">🇮🇩</span> IHSG Signals
        </h2>
        {loaded ? (
          <div className="grid-3">
            {ihsgTickers.map((t, i) => (
              <div key={t.ticker} className={`fade-in fade-in-d${i + 1}`}>
                <SignalCard data={tickerDetails[t.ticker]} />
              </div>
            ))}
            {ihsgTickers.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No IHSG signals</p>}
          </div>
        ) : (
          <div className="loading"><div className="spinner" />Loading…</div>
        )}
      </div>

      {/* US section */}
      <div>
        <h2 className="section-title">
          <span className="emoji">🇺🇸</span> US Signals
        </h2>
        {loaded ? (
          <div className="grid-3">
            {usTickers.map((t, i) => (
              <div key={t.ticker} className={`fade-in fade-in-d${i + 1}`}>
                <SignalCard data={tickerDetails[t.ticker]} />
              </div>
            ))}
            {usTickers.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No US signals</p>}
          </div>
        ) : (
          <div className="loading"><div className="spinner" />Loading…</div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, icon, color, subtitle, delay = 0 }) {
  return (
    <div className={`glass-card stat-card fade-in fade-in-d${delay + 1}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: '1.1rem' }}>{icon}</span>
        <span className="label">{label}</span>
      </div>
      <div className="value" style={{ color: color || 'var(--text-primary)' }}>{value}</div>
      {subtitle && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>{subtitle}</div>}
    </div>
  )
}
