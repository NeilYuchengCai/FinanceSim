import { useState, useCallback, lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import CommandPalette from './components/CommandPalette'
import { allLazyRoutes } from './routes'

// Loading 组件
const PageLoader = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '400px',
    color: 'var(--text-secondary)'
  }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
      <div>加载中...</div>
    </div>
  </div>
)

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
    { path: '/', label: '概览', icon: '📊' },
    { path: '/markets', label: '市场', icon: '📈' },
    { path: '/equities', label: '股票', icon: '📉' },
    { path: '/fx', label: '外汇', icon: '💱' },
    { path: '/bonds', label: '债券', icon: '🏛️' },
    { path: '/commodities', label: '商品', icon: '🛢️' },
    { path: '/bots', label: 'AI交易员', icon: '🤖' },
    { path: '/timeline', label: '时间线', icon: '⏳' },
    { path: '/portfolio', label: '投资组合', icon: '💼' },
    { path: '/orders', label: '订单', icon: '📋' },
    { path: '/news', label: '新闻', icon: '📰' },
    { path: '/search', label: '搜索', icon: '🔍' },
    { path: '/analytics', label: '分析', icon: '🔬' },
    { path: '/economy', label: '宏观经济', icon: '🌍' },
    { path: '/simulation', label: '模拟', icon: '▶️' },
    { path: '/challenges', label: '挑战', icon: '🏆' },
    { path: '/settings', label: '设置', icon: '⚙️' },
    { path: '/create-world', label: '创建世界', icon: '🌐' },
  ]

  // 动态组件映射
  const routeComponents = {
    '/': lazy(allLazyRoutes.Overview),
    '/markets': lazy(allLazyRoutes.Markets),
    '/equities': lazy(allLazyRoutes.Equities),
    '/fx': lazy(allLazyRoutes.FX),
    '/bonds': lazy(allLazyRoutes.Bonds),
    '/commodities': lazy(allLazyRoutes.Commodities),
    '/bots': lazy(allLazyRoutes.Bots),
    '/timeline': lazy(allLazyRoutes.Timeline),
    '/portfolio': lazy(allLazyRoutes.Portfolio),
    '/orders': lazy(allLazyRoutes.Orders),
    '/news': lazy(allLazyRoutes.News),
    '/search': lazy(allLazyRoutes.Search),
    '/analytics': lazy(allLazyRoutes.Analytics),
    '/economy': lazy(allLazyRoutes.Economy),
    '/simulation': lazy(allLazyRoutes.Simulation),
    '/challenges': lazy(allLazyRoutes.Challenges),
    '/settings': lazy(allLazyRoutes.Settings),
    '/create-world': lazy(allLazyRoutes.WorldCreator),
  }

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
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {Object.entries(routeComponents).map(([path, Component]) => (
                <Route key={path} path={path} element={<Component />} />
              ))}
            </Routes>
          </Suspense>
        </main>
        <CommandPalette isOpen={paletteOpen} onClose={closePalette} />
      </div>
    </Router>
  )
}

export default App
