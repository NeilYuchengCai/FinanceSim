import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { t } from '../i18n'

interface Command {
  id: string
  title: string
  subtitle?: string
  icon: string
  action: () => void
  keywords?: string[]
}

/**
 * 命令 id -> 真实路由的显式映射。
 * 路由注册以 App.tsx 的 routeComponents 为唯一事实来源；
 * NAV_COMMANDS 里没有映射的 id 会被过滤掉，不会生成不存在的 /nav-xxx 路径。
 */
const NAV_ROUTES: Record<string, string> = {
  'nav-overview': '/',
  'nav-markets': '/markets',
  'nav-equities': '/equities',
  'nav-fx': '/fx',
  'nav-bonds': '/bonds',
  'nav-commodities': '/commodities',
  'nav-bots': '/bots',
  'nav-timeline': '/timeline',
  'nav-portfolio': '/portfolio',
  'nav-orders': '/orders',
  'nav-news': '/news',
  'nav-search': '/search',
  'nav-analytics': '/analytics',
  'nav-economy': '/economy',
  'nav-simulation': '/simulation',
  'nav-challenges': '/challenges',
  'nav-settings': '/settings',
  'nav-create-world': '/create-world',
}

interface NavCommandDef {
  id: string
  icon: string
  navKey: string
  subKey: string
  keywords: string[]
}

const NAV_COMMAND_DEFS: NavCommandDef[] = [
  { id: 'nav-overview', icon: '📊', navKey: 'nav.overview', subKey: 'palette.subOverview', keywords: ['概览', '总览', 'overview'] },
  { id: 'nav-markets', icon: '📈', navKey: 'nav.markets', subKey: 'palette.subMarkets', keywords: ['市场', 'markets'] },
  { id: 'nav-equities', icon: '📉', navKey: 'nav.equities', subKey: 'palette.subEquities', keywords: ['股票', 'equity', '美股', 'a股'] },
  { id: 'nav-fx', icon: '💱', navKey: 'nav.fx', subKey: 'palette.subFx', keywords: ['外汇', 'fx', 'currency'] },
  { id: 'nav-bonds', icon: '🏛️', navKey: 'nav.bonds', subKey: 'palette.subBonds', keywords: ['债券', 'bond', '国债'] },
  { id: 'nav-commodities', icon: '🛢️', navKey: 'nav.commodities', subKey: 'palette.subCommodities', keywords: ['商品', 'commodities', '原油', '黄金'] },
  { id: 'nav-bots', icon: '🤖', navKey: 'nav.bots', subKey: 'palette.subBots', keywords: ['机器人', 'bot', '交易员'] },
  { id: 'nav-timeline', icon: '⏳', navKey: 'nav.timeline', subKey: 'palette.subTimeline', keywords: ['时间线', 'timeline', '事件'] },
  { id: 'nav-portfolio', icon: '💼', navKey: 'nav.portfolio', subKey: 'palette.subPortfolio', keywords: ['组合', 'portfolio', '持仓'] },
  { id: 'nav-orders', icon: '📋', navKey: 'nav.orders', subKey: 'palette.subOrders', keywords: ['订单', 'orders', '下单'] },
  { id: 'nav-news', icon: '📰', navKey: 'nav.news', subKey: 'palette.subNews', keywords: ['新闻', 'news'] },
  { id: 'nav-search', icon: '🔍', navKey: 'nav.search', subKey: 'palette.subSearch', keywords: ['搜索', 'search', '查找'] },
  { id: 'nav-analytics', icon: '🔬', navKey: 'nav.analytics', subKey: 'palette.subAnalytics', keywords: ['分析', 'analytics'] },
  { id: 'nav-economy', icon: '🌍', navKey: 'nav.economy', subKey: 'palette.subEconomy', keywords: ['经济', 'economy', '宏观'] },
  { id: 'nav-simulation', icon: '▶️', navKey: 'nav.simulation', subKey: 'palette.subSimulation', keywords: ['模拟', 'simulation', '控制'] },
  { id: 'nav-challenges', icon: '🏆', navKey: 'nav.challenges', subKey: 'palette.subChallenges', keywords: ['挑战', 'challenges'] },
  { id: 'nav-settings', icon: '⚙️', navKey: 'nav.settings', subKey: 'palette.subSettings', keywords: ['设置', 'settings'] },
  { id: 'nav-create-world', icon: '🌐', navKey: 'nav.createWorld', subKey: 'palette.subCreateWorld', keywords: ['世界', 'world', '创建'] },
]

function buildNavCommands(navigate: (path: string) => void, onClose: () => void): Command[] {
  const commands: Command[] = []
  for (const def of NAV_COMMAND_DEFS) {
    const path = NAV_ROUTES[def.id]
    if (!path) continue // 没有注册路由的命令不进面板，避免跳空白页
    commands.push({
      id: def.id,
      title: t(def.navKey, def.id),
      subtitle: t(def.subKey, ''),
      icon: def.icon,
      keywords: def.keywords,
      action: () => {
        navigate(path)
        onClose()
      },
    })
  }
  return commands
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  const allCommands: Command[] = buildNavCommands(navigate, onClose)

  const filtered = allCommands.filter(cmd => {
    if (!query.trim()) return true
    const search = query.toLowerCase()
    const titleMatch = cmd.title.toLowerCase().includes(search)
    const subMatch = cmd.subtitle?.toLowerCase().includes(search)
    const kwMatch = cmd.keywords?.some(k => k.toLowerCase().includes(search))
    return titleMatch || subMatch || !!kwMatch
  })

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!isOpen) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = filtered[selectedIndex]
      if (cmd) {
        cmd.action()
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    }
  }, [isOpen, filtered, selectedIndex, onClose])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      paddingTop: '15vh',
      background: 'rgba(0,0,0,0.6)',
      backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div style={{
        width: 'min(640px, 90vw)',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        overflow: 'hidden',
      }} onClick={e => e.stopPropagation()}>
        {/* Search input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <span style={{ fontSize: 20, color: 'var(--text-secondary)' }}>🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t('palette.placeholder', '搜索命令或页面...')}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: 16,
            }}
          />
          <kbd className="kbd">ESC</kbd>
        </div>

        {/* Results */}
        <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              {t('palette.noResults', '无匹配结果')}
            </div>
          ) : (
            filtered.map((cmd, i) => (
              <div
                key={cmd.id}
                onClick={cmd.action}
                onMouseEnter={() => setSelectedIndex(i)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 20px',
                  cursor: 'pointer',
                  background: i === selectedIndex ? 'var(--bg-tertiary)' : 'transparent',
                  transition: 'background 0.1s',
                }}
              >
                <span style={{ fontSize: 18, width: 28, textAlign: 'center' }}>{cmd.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{cmd.title}</div>
                  {cmd.subtitle && (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{cmd.subtitle}</div>
                  )}
                </div>
                {i === selectedIndex && <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>↵</span>}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '10px 20px',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          gap: 16,
          fontSize: 12,
          color: 'var(--text-secondary)',
        }}>
          <span><kbd className="kbd">↑</kbd><kbd className="kbd">↓</kbd> {t('palette.navigate', '导航')}</span>
          <span><kbd className="kbd">↵</kbd> {t('palette.select', '选择')}</span>
          <span><kbd className="kbd">ESC</kbd> {t('palette.close', '关闭')}</span>
        </div>
      </div>
    </div>
  )
}
