import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/ihsg', label: 'IHSG', icon: '🇮🇩' },
  { path: '/us', label: 'US Stocks', icon: '🇺🇸' },
  { path: '/backtest', label: 'Backtest', icon: '📈' },
]

export default function Header() {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header style={{
      background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border-color)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      backdropFilter: 'blur(16px)',
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 60,
      }}>
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '1.5rem' }}>⚡</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 800,
            fontSize: '1.1rem',
            background: 'linear-gradient(135deg, var(--green), var(--blue))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.02em',
          }}>
            NajibTrader
          </span>
        </Link>

        {/* Desktop nav */}
        <nav style={{ display: 'flex', gap: 4 }} className="desktop-nav">
          {NAV_ITEMS.map(item => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  background: isActive ? 'var(--bg-card)' : 'transparent',
                  textDecoration: 'none',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="mobile-menu-btn"
          style={{
            display: 'none',
            background: 'none',
            border: 'none',
            color: 'var(--text-primary)',
            fontSize: '1.4rem',
            cursor: 'pointer',
          }}
        >
          {menuOpen ? '✕' : '☰'}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div style={{
          padding: '8px 20px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          borderTop: '1px solid var(--border-color)',
        }} className="mobile-menu">
          {NAV_ITEMS.map(item => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMenuOpen(false)}
                style={{
                  padding: '10px 16px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  background: isActive ? 'var(--bg-card)' : 'transparent',
                  textDecoration: 'none',
                }}
              >
                {item.icon} {item.label}
              </Link>
            )
          })}
        </div>
      )}

      <style>{`
        @media (max-width: 640px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: block !important; }
        }
        @media (min-width: 641px) {
          .mobile-menu { display: none !important; }
        }
      `}</style>
    </header>
  )
}
