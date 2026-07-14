import { useState, useEffect, createContext, useContext } from 'react'
import { HashRouter, Routes, Route, useParams } from 'react-router-dom'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import SignalTable from './components/SignalTable'
import BacktestPanel from './components/BacktestPanel'
import TickerDetail from './components/TickerDetail'
import DisclaimerFooter from './components/DisclaimerFooter'

const DataContext = createContext(null)
export const useData = () => useContext(DataContext)

const DATA_BASE = import.meta.env.DEV ? '/data' : './data'

function App() {
  const [signals, setSignals] = useState(null)
  const [backtest, setBacktest] = useState(null)
  const [tickerData, setTickerData] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadData() {
      try {
        const [indexRes, btRes] = await Promise.all([
          fetch(`${DATA_BASE}/signals/index.json`),
          fetch(`${DATA_BASE}/backtest.json`),
        ])
        if (!indexRes.ok || !btRes.ok) throw new Error('Failed to fetch data')
        setSignals(await indexRes.json())
        setBacktest(await btRes.json())
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const loadTicker = async (ticker) => {
    if (tickerData[ticker]) return tickerData[ticker]
    const safeName = ticker.replace('.', '_')
    try {
      const res = await fetch(`${DATA_BASE}/signals/${safeName}.json`)
      if (!res.ok) throw new Error(`Failed to load ${ticker}`)
      const data = await res.json()
      setTickerData(prev => ({ ...prev, [ticker]: data }))
      return data
    } catch (e) {
      console.error(e)
      setTickerData(prev => ({ ...prev, [ticker]: { failed: true } }))
      return null
    }
  }

  return (
    <DataContext.Provider value={{ signals, backtest, tickerData, loadTicker, loading, error }}>
      <HashRouter>
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
          <Header />
          <main style={{ flex: 1, paddingTop: 20, paddingBottom: 20 }}>
            <div className="container">
              {loading ? (
                <div className="loading"><div className="spinner" />Loading signal data…</div>
              ) : error ? (
                <div className="loading" style={{ color: 'var(--red)' }}>⚠ {error}</div>
              ) : (
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/ihsg" element={<SignalTable market="IHSG" />} />
                  <Route path="/us" element={<SignalTable market="US" />} />
                  <Route path="/backtest" element={<BacktestPanel />} />
                  <Route path="/ticker/:ticker" element={<TickerDetailWrapper />} />
                </Routes>
              )}
            </div>
          </main>
          <DisclaimerFooter />
        </div>
      </HashRouter>
    </DataContext.Provider>
  )
}

function TickerDetailWrapper() {
  const { ticker } = useParams()
  return <TickerDetail ticker={decodeURIComponent(ticker)} />
}

export default App
