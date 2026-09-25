import { useState, useCallback } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import Overview from './pages/Overview'
import Markets from './pages/Markets'
import Equities from './pages/Equities'
import FX from './pages/FX'
import Bonds from './pages/Bonds'
import Portfolio from './pages/Portfolio'
import Orders from './pages/Orders'
import News from './pages/News'
import Search from './pages/Search'
import Analytics from './pages/Analytics'
import Economy from './pages/Economy'
import Simulation from './pages/Simulation'
import Challenges from './pages/Challenges'
import Settings from './pages/Settings'
import WorldCreator from './pages/WorldCreator'
import Bots from './pages/Bots'
import Timeline from './pages/Timeline'
import CommandPalette from './components/CommandPalette'

function App() {
  const { theme, toggleTheme } = useTheme()
  const [paletteOpen, setPaletteOpen] = useState(false)

  const openPalette = useCallback(() => setPaletteOpen(true), [])
  const closePalette = useCallback(() => setPaletteOpen(false), [])

  // ⌘/Ctrl+K to open search
  useKeyboardShortcuts([
    {
      key: 'k',
      metaKey: true,
      action: openPalette,
      description: 'Open Command Palette'
    },
    {
      key: 'k',
      ctrlKey: true,
      action: openPalette,
      description: 'Open Command Palette'
    },
    {
      key: '/',
      action: openPalette,
      description: 'Open Command Palette (alternative)'
    }
  ])

  const navItems = [
    { path: '/', label: 'Overview', icon: '📊' },
    { path: '/markets', label: 'Markets', icon: '📈' },
    { path: '/equities', label: 'Equities', icon: '📉' },
    { path: '/fx', label: 'FX', icon: '💱' },
    { path: '/bonds', label: 'Bonds', icon: '🏛️' },
    { path: '/bots', label: 'Bots', icon: '🤖' },
    { path: '/timeline', label: 'Timeline', icon: '⏳' },
    { path: '/portfolio', label: 'Portfolio', icon: '💼' },
    { path: '/orders', label: 'Orders', icon: '📋' },
    { path: '/news', label: 'News', icon: '📰' },
    { path: '/search', label: 'Search', icon: '🔍' },
    { path: '/analytics', label: 'Analytics', icon: '🔬' },
    { path: '/economy', label: 'Economy', icon: '🌍' },
    { path: '/simulation', label: 'Simulation', icon: '▶️' },
    { path: '/challenges', label: 'Challenges', icon: '🏆' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
    { path: '/create-world', label: 'Create World', icon: '🌐' },
  ]

  return (
    <Router>
      <div className="app">
        <nav className="sidebar">
          <div className="logo">
            <h1>FinanceSim</h1>
          </div>
          <ul className="nav-menu">
            {navItems.map(item => (
              <li key={item.path}>
                <Link to={item.path}>
                  <span style={{ marginRight: 8 }}>{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-color)', marginTop: 'auto' }}>
            <button
              onClick={openPalette}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px dashed var(--border-color)',
                background: 'transparent',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              <span className="kbd">⌘</span><span className="kbd">K</span>
              <span style={{ marginLeft: 4 }}>Search...</span>
            </button>
          </div>
          <div style={{ padding: '0 20px 16px' }}>
            <button
              onClick={toggleTheme}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
            </button>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/markets" element={<Markets />} />
            <Route path="/equities" element={<Equities />} />
            <Route path="/fx" element={<FX />} />
            <Route path="/bonds" element={<Bonds />} />
            <Route path="/bots" element={<Bots />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/news" element={<News />} />
            <Route path="/search" element={<Search />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/economy" element={<Economy />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/challenges" element={<Challenges />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/create-world" element={<WorldCreator />} />
          </Routes>
        </main>
        <CommandPalette isOpen={paletteOpen} onClose={closePalette} />
      </div>
    </Router>
  )
}

export default App
