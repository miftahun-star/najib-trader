import { useState } from 'react'
import { useData } from '../App'

export default function BacktestPanel() {
  const { backtest } = useData()
  const [selectedMarket, setSelectedMarket] = useState('overall')

  if (!backtest) return <div className="loading">No backtest data available</div>

  const markets = ['overall', 'IHSG', 'US']
  const data = selectedMarket === 'overall'
    ? backtest.overall
    : backtest.markets?.[selectedMarket]

  const byTimeframe = selectedMarket !== 'overall'
    ? backtest.markets?.[selectedMarket]?.by_timeframe || {}
    : {}

  return (
    <div>
      <h1 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: 4 }}>📈 Backtest Results</h1>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 20 }}>
        Live backtested statistics — this is the real accuracy, not a claim.
        <br />Last updated: {backtest.last_updated || '—'}
      </p>

      {/* Market tabs */}
      <div className="tab-nav">
        {markets.map(m => (
          <button
            key={m}
            className={`tab-btn ${selectedMarket === m ? 'active' : ''}`}
            onClick={() => setSelectedMarket(m)}
          >
            {m === 'overall' ? '🌐 Overall' : m === 'IHSG' ? '🇮🇩 IHSG' : '🇺🇸 US'}
          </button>
        ))}
      </div>

      {data ? (
        <div>
          {/* Main stats */}
          <div className="grid-4" style={{ marginBottom: 24 }}>
            <MetricCard label="Win Rate" value={`${data.win_rate || 0}%`} color="var(--green)" icon="🎯" />
            <MetricCard label="Avg R-Multiple" value={data.avg_r || 0} color="var(--blue)" icon="📊" />
            <MetricCard label="Max Drawdown" value={`${data.max_dd || 0}R`} color="var(--red)" icon="📉" />
            <MetricCard label="Sample Size" value={`n=${data.n_trades || 0}`} color="var(--text-secondary)" icon="🔢" />
          </div>

          {/* Win rate bar */}
          <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: 16 }}>Win Rate Distribution</h3>

            <div className="bt-bar-container">
              <span className="bt-bar-label">Wins</span>
              <div className="bt-bar-track">
                <div className="bt-bar-fill" style={{
                  width: `${data.win_rate || 0}%`,
                  background: 'linear-gradient(90deg, var(--green), #34d399)',
                }} />
              </div>
              <span className="bt-bar-value" style={{ color: 'var(--green)' }}>{data.win_rate || 0}%</span>
            </div>

            <div className="bt-bar-container">
              <span className="bt-bar-label">Losses</span>
              <div className="bt-bar-track">
                <div className="bt-bar-fill" style={{
                  width: `${100 - (data.win_rate || 0)}%`,
                  background: 'linear-gradient(90deg, var(--red), #fb7185)',
                }} />
              </div>
              <span className="bt-bar-value" style={{ color: 'var(--red)' }}>{(100 - (data.win_rate || 0)).toFixed(1)}%</span>
            </div>
          </div>

          {/* By timeframe */}
          {Object.keys(byTimeframe).length > 0 && (
            <div className="glass-card" style={{ padding: 24 }}>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: 16 }}>By Timeframe</h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timeframe</th>
                    <th>Win Rate</th>
                    <th>Avg R</th>
                    <th>Max DD</th>
                    <th>Trades</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(byTimeframe).map(([tf, stats]) => (
                    <tr key={tf}>
                      <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{tf}</td>
                      <td className="mono" style={{ color: stats.win_rate >= 50 ? 'var(--green)' : 'var(--red)' }}>
                        {stats.win_rate}%
                      </td>
                      <td className="mono">{stats.avg_r}</td>
                      <td className="mono" style={{ color: 'var(--red)' }}>{stats.max_dd}R</td>
                      <td className="mono">{stats.n_trades}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          No backtest data for {selectedMarket}
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, color, icon }) {
  return (
    <div className="glass-card stat-card fade-in">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: '1rem' }}>{icon}</span>
        <span className="label">{label}</span>
      </div>
      <div className="value" style={{ color }}>{value}</div>
    </div>
  )
}
