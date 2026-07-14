import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../App'
import ScoreGauge from './ScoreGauge'
import TimeframeBadge from './TimeframeBadge'

export default function TickerDetail({ ticker }) {
  const { loadTicker } = useData()
  const [data, setData] = useState(null)
  const [selectedTf, setSelectedTf] = useState('daily')
  const [loading, setLoading] = useState(true)
  const chartRef = useRef(null)
  const chartInstance = useRef(null)

  useEffect(() => {
    async function load() {
      const d = await loadTicker(ticker)
      setData(d)
      setLoading(false)
    }
    load()
  }, [ticker])

  // Initialize lightweight chart
  useEffect(() => {
    if (!chartRef.current || !data) return

    let chart
    async function initChart() {
      try {
        const { createChart } = await import('lightweight-charts')

        // Clean up previous chart
        if (chartInstance.current) {
          chartInstance.current.remove()
        }

        chart = createChart(chartRef.current, {
          width: chartRef.current.clientWidth,
          height: 400,
          layout: {
            background: { color: 'transparent' },
            textColor: '#94a3b8',
            fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace",
          },
          grid: {
            vertLines: { color: 'rgba(99, 115, 148, 0.08)' },
            horzLines: { color: 'rgba(99, 115, 148, 0.08)' },
          },
          crosshair: {
            mode: 0,
            vertLine: { color: 'rgba(99, 115, 148, 0.3)', style: 2 },
            horzLine: { color: 'rgba(99, 115, 148, 0.3)', style: 2 },
          },
          rightPriceScale: {
            borderColor: 'rgba(99, 115, 148, 0.2)',
          },
          timeScale: {
            borderColor: 'rgba(99, 115, 148, 0.2)',
            timeVisible: false,
          },
        })

        // Generate sample OHLCV data for the chart from the ticker's indicators
        const tf = data.timeframes?.[selectedTf]
        const price = tf?.indicators?.price || 100
        const atr = tf?.indicators?.atr || price * 0.02

        // Generate synthetic candlestick data for display
        const bars = generateSampleBars(price, atr, 120)

        const candleSeries = chart.addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#f43f5e',
          borderUpColor: '#10b981',
          borderDownColor: '#f43f5e',
          wickUpColor: '#10b981',
          wickDownColor: '#f43f5e',
        })
        candleSeries.setData(bars)

        // Add MA50 line
        if (tf?.indicators?.ma50) {
          const ma50Series = chart.addLineSeries({
            color: '#3b82f6',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          })
          const ma50Data = bars.slice(50).map((b, i) => ({
            time: b.time,
            value: bars.slice(i, i + 50).reduce((s, x) => s + x.close, 0) / 50,
          }))
          if (ma50Data.length > 0) ma50Series.setData(ma50Data)
        }

        // Add signal marker
        const signal = tf?.signal
        if (signal === 'BOTTOM' || signal === 'PEAK') {
          const lastBar = bars[bars.length - 1]
          candleSeries.setMarkers([{
            time: lastBar.time,
            position: signal === 'BOTTOM' ? 'belowBar' : 'aboveBar',
            color: signal === 'BOTTOM' ? '#10b981' : '#f43f5e',
            shape: signal === 'BOTTOM' ? 'arrowUp' : 'arrowDown',
            text: signal,
          }])
        }

        chart.timeScale().fitContent()
        chartInstance.current = chart

        // Resize handler
        const handleResize = () => {
          if (chartRef.current && chart) {
            chart.applyOptions({ width: chartRef.current.clientWidth })
          }
        }
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
      } catch (e) {
        console.error('Chart init error:', e)
      }
    }

    initChart()
    return () => {
      if (chartInstance.current) {
        chartInstance.current.remove()
        chartInstance.current = null
      }
    }
  }, [data, selectedTf])

  if (loading) return <div className="loading"><div className="spinner" />Loading {ticker}…</div>
  if (!data) return <div className="loading">No data for {ticker}</div>

  const tf = data.timeframes?.[selectedTf] || {}
  const ind = tf.indicators || {}
  const tl = tf.trade_levels || {}
  const patterns = tf.patterns || {}
  const yearly = data.yearly_trend || {}

  return (
    <div>
      <Link to="/" className="back-link">← Back to Dashboard</Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <h1 style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1.6rem' }}>{ticker}</h1>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', background: 'var(--bg-secondary)', padding: '4px 12px', borderRadius: 999 }}>
          {data.market}
        </span>
        {data.data_stale && (
          <span style={{ fontSize: '0.7rem', color: 'var(--amber)', background: 'var(--amber-dim)', padding: '4px 10px', borderRadius: 999 }}>
            ⚠ Stale Data
          </span>
        )}
      </div>

      {/* Timeframe selector */}
      <div className="tab-nav">
        {Object.keys(data.timeframes || {}).map(tfKey => (
          <button
            key={tfKey}
            className={`tab-btn ${selectedTf === tfKey ? 'active' : ''}`}
            onClick={() => setSelectedTf(tfKey)}
          >
            {tfKey.charAt(0).toUpperCase() + tfKey.slice(1)}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="glass-card" style={{ padding: 16, marginBottom: 24 }}>
        <div ref={chartRef} className="chart-container" />
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Signal & Score */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4 }}>Signal</div>
              <span className={`signal-badge ${tf.signal?.toLowerCase()}`}>
                <span className="dot" />{tf.signal || 'HOLD'}
              </span>
            </div>
            <ScoreGauge score={tf.score || 50} size={80} />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{tf.reason || ''}</div>

          {/* Score components */}
          {tf.components && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 8 }}>Score Breakdown</div>
              {Object.entries(tf.components).map(([key, val]) => (
                <div key={key} className="bt-bar-container" style={{ marginBottom: 4 }}>
                  <span className="bt-bar-label" style={{ width: 120, fontSize: '0.68rem' }}>{formatKey(key)}</span>
                  <div className="bt-bar-track">
                    <div className="bt-bar-fill" style={{
                      width: `${val}%`,
                      background: val >= 60 ? 'var(--green)' : val <= 40 ? 'var(--red)' : 'var(--slate)',
                    }} />
                  </div>
                  <span className="bt-bar-value" style={{ width: 40 }}>{val}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Trade Levels */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 12 }}>Trade Levels</div>
          {tl.entry ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <LevelRow label="Entry" value={tl.entry} />
              <LevelRow label="Stop Loss" value={tl.stop_loss} color="var(--red)" />
              <LevelRow label="TP1 (1R)" value={tl.tp1} color="var(--green)" />
              <LevelRow label="TP2 (2R)" value={tl.tp2} color="var(--green)" />
              <LevelRow label="TP3 (3R)" value={tl.tp3} color="var(--green)" />
              <LevelRow label="Trail Stop" value={tl.trailing_stop} color="var(--amber)" />
              <div style={{ gridColumn: '1 / -1' }}>
                <LevelRow label="Risk (ATR)" value={tl.risk} />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <LevelRow label="R:R Ratio" value={tl.rr_ratio} />
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No active trade levels (signal is {tf.signal})</div>
          )}
        </div>
      </div>

      {/* Indicators */}
      <div className="glass-card" style={{ padding: 20, marginBottom: 24 }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 12 }}>Technical Indicators</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
          <IndRow label="RSI(14)" value={ind.rsi} warn={ind.rsi < 30 || ind.rsi > 70} />
          <IndRow label="Stoch %K" value={ind.stoch_k} />
          <IndRow label="Stoch %D" value={ind.stoch_d} />
          <IndRow label="MACD" value={ind.macd} />
          <IndRow label="MACD Signal" value={ind.macd_signal} />
          <IndRow label="MACD Hist" value={ind.macd_hist} color={ind.macd_hist > 0 ? 'var(--green)' : 'var(--red)'} />
          <IndRow label="BB Upper" value={ind.bb_upper} />
          <IndRow label="BB Mid" value={ind.bb_mid} />
          <IndRow label="BB Lower" value={ind.bb_lower} />
          <IndRow label="ATR(14)" value={ind.atr} />
          <IndRow label="MA50" value={ind.ma50} />
          <IndRow label="MA200" value={ind.ma200} />
          <IndRow label="Vol Ratio" value={ind.vol_ratio} warn={ind.vol_ratio >= 2} />
        </div>
      </div>

      {/* Patterns */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 12 }}>Pattern Detection</div>
          <PatternRow label="Candle Pattern" value={patterns.candle?.name || 'None'} sub={patterns.candle?.direction} />
          <PatternRow label="Bullish Divergence" value={patterns.bullish_divergence ? '✅ Yes' : '—'} />
          <PatternRow label="Bearish Divergence" value={patterns.bearish_divergence ? '✅ Yes' : '—'} />
          <PatternRow label="BB Touch" value={patterns.bb_touch || 'None'} />
          <PatternRow label="Volume Climax" value={patterns.volume_climax ? '🔥 Yes' : '—'} />
          <PatternRow label="Near Support" value={patterns.near_support ? '✅ Yes' : '—'} />
          <PatternRow label="Near Resistance" value={patterns.near_resistance ? '✅ Yes' : '—'} />
          <PatternRow label="In Fib Zone" value={patterns.in_fib_zone ? '✅ Yes' : '—'} />
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 12 }}>Yearly Trend Bias</div>
          <PatternRow label="Bias" value={yearly.bias || 'neutral'} />
          <PatternRow label="MA200 Position" value={yearly.ma200_position || '—'} />
          <PatternRow label="Structure" value={yearly.structure || '—'} />
          <div style={{ marginTop: 12, fontSize: '0.68rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            {yearly.description || 'Long-term trend bias — not a reversal call'}
          </div>

          {/* S/R Levels */}
          {(tf.support_levels?.length > 0 || tf.resistance_levels?.length > 0) && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 8 }}>S/R Levels</div>
              {tf.support_levels?.map((s, i) => (
                <div key={`s${i}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 2 }}>
                  <span style={{ color: 'var(--green)' }}>Support</span>
                  <span className="mono">{s}</span>
                </div>
              ))}
              {tf.resistance_levels?.map((r, i) => (
                <div key={`r${i}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 2 }}>
                  <span style={{ color: 'var(--red)' }}>Resistance</span>
                  <span className="mono">{r}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function LevelRow({ label, value, color }) {
  if (value == null) return null
  return (
    <div>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 2 }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        fontSize: '0.85rem',
        color: color || 'var(--text-primary)',
      }}>
        {typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}
      </div>
    </div>
  )
}

function IndRow({ label, value, color, warn }) {
  return (
    <div style={{ padding: '6px 0' }}>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        fontSize: '0.8rem',
        color: color || (warn ? 'var(--amber)' : 'var(--text-primary)'),
      }}>
        {value != null ? (typeof value === 'number' ? value.toFixed(2) : String(value)) : '—'}
      </div>
    </div>
  )
}

function PatternRow({ label, value, sub }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', fontSize: '0.75rem' }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontWeight: 500 }}>
        {value}
        {sub && <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>({sub})</span>}
      </span>
    </div>
  )
}

function formatKey(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function generateSampleBars(currentPrice, atr, count) {
  const bars = []
  const now = new Date()
  let price = currentPrice * 0.85

  for (let i = count; i > 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    // Skip weekends
    if (date.getDay() === 0 || date.getDay() === 6) continue

    const change = (Math.random() - 0.48) * atr * 0.8
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * atr * 0.3
    const low = Math.min(open, close) - Math.random() * atr * 0.3
    price = close

    bars.push({
      time: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
    })
  }
  return bars
}
