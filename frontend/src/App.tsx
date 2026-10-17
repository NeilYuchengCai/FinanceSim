import { useState, useCallback, lazy, Suspense, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import CommandPalette from './components/CommandPalette'
import GlobalClock from './components/GlobalClock'
import ErrorBoundary from './components/ErrorBoundary'
import { ToastProvider } from './components/Toast'
import { allLazyRoutes } from './routes'
import { t, useLanguage } from './i18n'
import { restoreLatestSave } from './services/saveSystem'
import { loadFxRates } from './services/fxRates'

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
        <div>{t('common.loading')}</div>
      </div>
  </div>
)

function App() {
  const { theme, toggleTheme } = useTheme()
  // 订阅语言变化，切换语言时让整棵子树（含侧边栏）重渲染
  const { language } = useLanguage()
  const [paletteOpen, setPaletteOpen] = useState(false)

  const openPalette = useCallback(() => setPaletteOpen(true), [])
  const closePalette = useCallback(() => setPaletteOpen(false), [])

  // 启动时尝试从本地存档恢复世界状态；无存档则保持后端默认（从零开始）
  useEffect(() => {
    restoreLatestSave().catch((err) => {
      console.warn('Failed to restore latest save:', err)
    })
    // 预拉取 FX 汇率，供"展示货币切换"实时换算（失败则退化为不换算，不影响运行）
    loadFxRates().catch((err) => {
      console.warn('Failed to load FX rates:', err)
    })
  }, [])

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
    { path: '/', label: t('nav.overview'), icon: '📊' },
    { path: '/markets', label: t('nav.markets'), icon: '📈' },
    { path: '/equities', label: t('nav.equities'), icon: '📉' },
    { path: '/fx', label: t('nav.fx'), icon: '💱' },
    { path: '/bonds', label: t('nav.bonds'), icon: '🏛️' },
    { path: '/commodities', label: t('nav.commodities'), icon: '🛢️' },
    { path: '/bots', label: t('nav.bots'), icon: '🤖' },
    { path: '/timeline', label: t('nav.timeline'), icon: '⏳' },
    { path: '/portfolio', label: t('nav.portfolio'), icon: '💼' },
    { path: '/orders', label: t('nav.orders'), icon: '📋' },
    { path: '/news', label: t('nav.news'), icon: '📰' },
    { path: '/search', label: t('nav.search'), icon: '🔍' },
    { path: '/analytics', label: t('nav.analytics'), icon: '🔬' },
    { path: '/economy', label: t('nav.economy'), icon: '🌍' },
    { path: '/simulation', label: t('nav.simulation'), icon: '▶️' },
    { path: '/challenges', label: t('nav.challenges'), icon: '🏆' },
    { path: '/settings', label: t('nav.settings'), icon: '⚙️' },
    { path: '/create-world', label: t('nav.createWorld'), icon: '🌐' },
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
    '/asset/:ticker': lazy(allLazyRoutes.AssetDetail),
  }

  return (
    <ToastProvider>
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
                <span style={{ marginLeft: 4 }}>{t('common.search')}</span>
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
                {/* nav 块暂无主题键，兜底按当前语言取；日后同事补上 nav.themeLight/themeDark 即自动生效 */}
                {theme === 'dark'
                  ? `☀️ ${t('nav.themeLight', language === 'en' ? 'Light Mode' : '浅色模式')}`
                  : `🌙 ${t('nav.themeDark', language === 'en' ? 'Dark Mode' : '深色模式')}`}
              </button>
            </div>
          </nav>
          <main className="main-content" style={{ paddingRight: 220 }}>
            <Suspense fallback={<PageLoader />}>
              <ErrorBoundary label="page">
                <Routes>
                  {Object.entries(routeComponents).map(([path, Component]) => (
                    <Route key={path} path={path} element={<Component />} />
                  ))}
                </Routes>
              </ErrorBoundary>
            </Suspense>
          </main>
          <GlobalClock />
          <CommandPalette isOpen={paletteOpen} onClose={closePalette} />
        </div>
      </Router>
    </ToastProvider>
  )
}

export default App
