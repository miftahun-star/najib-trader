import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../App'
import SignalCard from './SignalCard'

export default function Dashboard() {
  const { signals, backtest, loadTicker } = useData()
  const [tickerDetails, setTickerDetails] = useState({})
  const [loaded, setLoaded] = useState(false)

  const tickers = signals?.tickers || []
  
  // Identify active opportunities (BOTTOM / PEAK signals)
  const activeTickers = tickers.filter(t => t.signal === 'BOTTOM' || t.signal === 'PEAK')

  useEffect(() => {
    if (!signals?.tickers) return
    
    if (activeTickers.length === 0) {
      setLoaded(true)
      return
    }

    async function loadActive() {
      try {
        // Fetch details in parallel for active signals only (prevents sequential fetching of 500+ items)
        const promises = activeTickers.map(t => loadTicker(t.ticker))
        const results = await Promise.all(promises)
        const details = {}
        activeTickers.forEach((t, index) => {
          if (results[index]) {
            details[t.ticker] = results[index]
          }
        })
        setTickerDetails(details)
      } catch (e) {
        console.error(e)
      } finally {
        setLoaded(true)
      }
    }
    
    loadActive()
  }, [signals])

  if (!signals) return null

  const ihsgActive = activeTickers.filter(t => t.market === 'IHSG')
  const usActive = activeTickers.filter(t => t.market === 'US')

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
          <span className="emoji">🇮🇩</span> Active IHSG Opportunities
        </h2>
        {loaded ? (
          <div className="grid-3">
            {ihsgActive.map((t, i) => {
              const detail = tickerDetails[t.ticker]
              if (!detail || detail.failed) return null
              return (
                <div key={t.ticker} className={`fade-in fade-in-d${i + 1}`}>
                  <SignalCard data={detail} />
                </div>
              )
            })}
            {ihsgActive.length === 0 && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No active buy/sell signals. View watchlists in the <Link to="/ihsg" style={{ color: 'var(--blue)' }}>IHSG List</Link>.
              </p>
            )}
          </div>
        ) : (
          <div className="loading"><div className="spinner" />Loading opportunities…</div>
        )}
      </div>

      {/* US section */}
      <div>
        <h2 className="section-title">
          <span className="emoji">🇺🇸</span> Active US Opportunities
        </h2>
        {loaded ? (
          <div className="grid-3">
            {usActive.map((t, i) => {
              const detail = tickerDetails[t.ticker]
              if (!detail || detail.failed) return null
              return (
                <div key={t.ticker} className={`fade-in fade-in-d${i + 1}`}>
                  <SignalCard data={detail} />
                </div>
              )
            })}
            {usActive.length === 0 && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No active buy/sell signals. View watchlists in the <Link to="/us" style={{ color: 'var(--blue)' }}>US Stock List</Link>.
              </p>
            )}
          </div>
        ) : (
          <div className="loading"><div className="spinner" />Loading opportunities…</div>
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
