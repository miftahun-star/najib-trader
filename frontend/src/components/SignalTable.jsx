import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../App'
import TimeframeBadge from './TimeframeBadge'

export default function SignalTable({ market }) {
  const { signals, loadTicker } = useData()
  const [tickerDetails, setTickerDetails] = useState({})
  const [filter, setFilter] = useState('ALL')
  const [sortKey, setSortKey] = useState('score')
  const [sortDir, setSortDir] = useState('desc')
  const [loaded, setLoaded] = useState(false)

  const tickers = (signals?.tickers || []).filter(t =>
    !market || t.market === market
  )

  useEffect(() => {
    async function load() {
      const details = {}
      for (const t of tickers) {
        const data = await loadTicker(t.ticker)
        if (data) details[t.ticker] = data
      }
      setTickerDetails(details)
      setLoaded(true)
    }
    load()
  }, [market, signals])

  const filtered = tickers.filter(t =>
    filter === 'ALL' || t.signal === filter
  )

  const sorted = [...filtered].sort((a, b) => {
    let va, vb
    if (sortKey === 'score') {
      va = a.score || 0
      vb = b.score || 0
    } else if (sortKey === 'ticker') {
      va = a.ticker
      vb = b.ticker
    } else if (sortKey === 'signal') {
      const order = { BOTTOM: 0, PEAK: 1, WATCH: 2, HOLD: 3 }
      va = order[a.signal] ?? 4
      vb = order[b.signal] ?? 4
    }
    if (sortDir === 'asc') return va > vb ? 1 : -1
    return va < vb ? 1 : -1
  })

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const title = market === 'IHSG' ? '🇮🇩 IHSG Signals' : market === 'US' ? '🇺🇸 US Stock Signals' : 'All Signals'

  return (
    <div>
      <h1 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: 20 }}>{title}</h1>

      {/* Filters */}
      <div className="filter-bar">
        {['ALL', 'BOTTOM', 'PEAK', 'WATCH', 'HOLD'].map(f => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'ALL' ? 'All' : f}
          </button>
        ))}
      </div>

      {!loaded ? (
        <div className="loading"><div className="spinner" />Loading…</div>
      ) : (
        <div className="glass-card" style={{ overflow: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('ticker')}>
                  Ticker {sortKey === 'ticker' && (sortDir === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('signal')}>
                  Signal {sortKey === 'signal' && (sortDir === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('score')}>
                  Score {sortKey === 'score' && (sortDir === 'asc' ? '↑' : '↓')}
                </th>
                <th>Price</th>
                <th>Entry</th>
                <th>SL</th>
                <th>TP1</th>
                <th>R:R</th>
                <th>Timeframes</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((t, i) => {
                const detail = tickerDetails[t.ticker]
                const daily = detail?.timeframes?.daily || {}
                const tl = daily.trade_levels || {}

                return (
                  <tr key={t.ticker} className={`fade-in fade-in-d${Math.min(i + 1, 4)}`}>
                    <td>
                      <Link to={`/ticker/${encodeURIComponent(t.ticker)}`} style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                      }}>
                        {t.ticker}
                      </Link>
                    </td>
                    <td>
                      <span className={`signal-badge ${t.signal?.toLowerCase()}`}>
                        <span className="dot" />
                        {t.signal}
                      </span>
                    </td>
                    <td className="mono">{t.score ?? '—'}</td>
                    <td className="mono">{fmtNum(t.price)}</td>
                    <td className="mono">{fmtNum(tl.entry)}</td>
                    <td className="mono red">{fmtNum(tl.stop_loss)}</td>
                    <td className="mono green">{fmtNum(tl.tp1)}</td>
                    <td className="mono" style={{ fontSize: '0.7rem' }}>{tl.rr_ratio || '—'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {detail?.timeframes && Object.keys(detail.timeframes).map(tf => (
                          <TimeframeBadge key={tf} timeframe={tf} />
                        ))}
                      </div>
                    </td>
                  </tr>
                )
              })}
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
                    No signals matching filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function fmtNum(val) {
  if (val == null || val === '') return '—'
  if (typeof val !== 'number') return val
  return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
