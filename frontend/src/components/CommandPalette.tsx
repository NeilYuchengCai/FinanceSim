import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

interface Command {
  id: string
  title: string
  subtitle?: string
  icon: string
  action: () => void
  keywords?: string[]
}

const NAV_COMMANDS: Command[] = [
  { id: 'nav-overview', title: 'Overview', subtitle: '市场概览', icon: '📊', action: () => {}, keywords: ['概览', '总览', 'overview'] },
  { id: 'nav-markets', title: 'Markets', subtitle: '市场总览', icon: '📈', action: () => {}, keywords: ['市场', 'markets'] },
  { id: 'nav-equities', title: 'Equities', subtitle: '股票', icon: '📉', action: () => {}, keywords: ['股票', 'equity', '美股', 'a股'] },
  { id: 'nav-fx', title: 'FX', subtitle: '外汇', icon: '💱', action: () => {}, keywords: ['外汇', 'fx', 'currency'] },
  { id: 'nav-bonds', title: 'Bonds', subtitle: '债券', icon: '🏛️', action: () => {}, keywords: ['债券', 'bond', '国债'] },
  { id: 'nav-bots', title: 'Bots', subtitle: '智能交易员', icon: '🤖', action: () => {}, keywords: ['机器人', 'bot', '交易员'] },
  { id: 'nav-timeline', title: 'Timeline', subtitle: '事件时间线', icon: '⏳', action: () => {}, keywords: ['时间线', 'timeline', '事件'] },
  { id: 'nav-portfolio', title: 'Portfolio', subtitle: '投资组合', icon: '💼', action: () => {}, keywords: ['组合', 'portfolio', '持仓'] },
  { id: 'nav-orders', title: 'Orders', subtitle: '订单管理', icon: '📋', action: () => {}, keywords: ['订单', 'orders', '下单'] },
  { id: 'nav-news', title: 'News', subtitle: '新闻', icon: '📰', action: () => {}, keywords: ['新闻', 'news'] },
  { id: 'nav-analytics', title: 'Analytics', subtitle: '分析', icon: '🔬', action: () => {}, keywords: ['分析', 'analytics'] },
  { id: 'nav-economy', title: 'Economy', subtitle: '宏观经济', icon: '🌍', action: () => {}, keywords: ['经济', 'economy', '宏观'] },
  { id: 'nav-simulation', title: 'Simulation', subtitle: '模拟控制', icon: '▶️', action: () => {}, keywords: ['模拟', 'simulation', '控制'] },
  { id: 'nav-settings', title: 'Settings', subtitle: '设置', icon: '⚙️', action: () => {}, keywords: ['设置', 'settings'] },
  { id: 'nav-search', title: 'Search', subtitle: '全局搜索', icon: '🔍', action: () => {}, keywords: ['搜索', 'search', '查找'] },
]

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  const allCommands: Command[] = [
    ...NAV_COMMANDS.map(cmd => ({
      ...cmd,
      action: () => {
        const path = `/nav-${cmd.id.split('-')[1]}`
        navigate(path)
        onClose()
      }
    })),
  ]

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
      setSelectedIndex(i => Math.max(i - 1, 0))
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
            placeholder="搜索命令或页面..."
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
              无匹配结果
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
          <span><kbd className="kbd">↑</kbd><kbd className="kbd">↓</kbd> 导航</span>
          <span><kbd className="kbd">↵</kbd> 选择</span>
          <span><kbd className="kbd">ESC</kbd> 关闭</span>
        </div>
      </div>
    </div>
  )
}
