import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../App'
import TimeframeBadge from './TimeframeBadge'

export default function SignalTable({ market }) {
  const { signals, loadTicker } = useData()
  const [tickerDetails, setTickerDetails] = useState({})
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('ALL')
  const [sortKey, setSortKey] = useState('score')
  const [sortDir, setSortDir] = useState('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 40

  const tickers = (signals?.tickers || []).filter(t =>
    !market || t.market === market
  )

  // Filter and Search
  const filtered = tickers.filter(t => {
    const matchesSignal = filter === 'ALL' || t.signal === filter
    const matchesSearch = t.ticker.toLowerCase().includes(search.toLowerCase())
    return matchesSignal && matchesSearch
  })

  // Sort
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
    } else if (sortKey === 'price') {
      va = a.price || 0
      vb = b.price || 0
    }
    if (sortDir === 'asc') return va > vb ? 1 : -1
    return va < vb ? 1 : -1
  })

  // Pagination
  const totalPages = Math.ceil(sorted.length / itemsPerPage)
  const paginated = sorted.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  useEffect(() => {
    setCurrentPage(1)
  }, [search, filter, market])

  // Load details dynamically for the current page only to prevent network overload
  useEffect(() => {
    async function loadPageDetails() {
      const details = { ...tickerDetails }
      let changed = false
      for (const t of paginated) {
        if (!details[t.ticker]) {
          const data = await loadTicker(t.ticker)
          if (data) {
            details[t.ticker] = data
            changed = true
          }
        }
      }
      if (changed) {
        setTickerDetails(details)
      }
    }
    if (paginated.length > 0) {
      loadPageDetails()
    }
  }, [currentPage, search, filter, market, signals])

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

      {/* Search and Filters */}
      <div className="filter-bar" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <input
          type="text"
          placeholder="🔍 Search ticker..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
          style={{
            flex: '1 1 200px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            padding: '8px 12px',
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
            outline: 'none',
          }}
        />
        
        <div style={{ display: 'flex', gap: 6 }}>
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
      </div>

      <div className="glass-card" style={{ overflow: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('ticker')} style={{ cursor: 'pointer' }}>
                Ticker {sortKey === 'ticker' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('signal')} style={{ cursor: 'pointer' }}>
                Signal {sortKey === 'signal' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('score')} style={{ cursor: 'pointer' }}>
                Score {sortKey === 'score' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>
                Price {sortKey === 'price' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th>Entry</th>
              <th>SL</th>
              <th>TP1</th>
              <th>R:R</th>
              <th>Timeframes</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((t, i) => {
              const detail = tickerDetails[t.ticker]
              const daily = detail?.timeframes?.daily || {}
              const tl = daily.trade_levels || {}

              return (
                <tr key={t.ticker} className="fade-in">
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
                      {detail?.timeframes ? (
                        Object.keys(detail.timeframes).map(tf => (
                          <TimeframeBadge key={tf} timeframe={tf} />
                        ))
                      ) : (
                        <div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} />
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
            {paginated.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
                  No signals matching criteria
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 20 }}>
          <button
            onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
            disabled={currentPage === 1}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: 'var(--bg-secondary)',
              color: currentPage === 1 ? 'var(--text-muted)' : 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
            }}
          >
            Previous
          </button>
          
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Page {currentPage} of {totalPages} ({filtered.length} total)
          </span>

          <button
            onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
            disabled={currentPage === totalPages}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: 'var(--bg-secondary)',
              color: currentPage === totalPages ? 'var(--text-muted)' : 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
            }}
          >
            Next
          </button>
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
