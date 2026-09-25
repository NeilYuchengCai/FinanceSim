import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'

interface Bot {
  name: string
  strategy: string
  cash: number
  positions: Record<string, number>
  total_trades: number
  total_pnl: number
  risk_tolerance: number
}

const STRATEGY_LABELS: Record<string, string> = {
  momentum: t('bots.momentum', '动量策略'),
  mean_reversion: t('bots.meanReversion', '均值回归'),
  market_making: t('bots.marketMaking', '做市商'),
  random: t('bots.random', '随机交易'),
  value: t('bots.value'),
  growth: t('bots.growth'),
  macro: t('bots.macro'),
  pairs: t('bots.pairs')
}

const STRATEGY_COLORS: Record<string, string> = {
  momentum: '#ef4444',
  mean_reversion: '#3b82f6',
  market_making: '#10b981',
  random: '#f59e0b',
  value: '#8b5cf6',
  growth: '#06b6d4',
  macro: '#f97316',
  pairs: '#ec4899'
}

export default function Bots() {
  const [bots, setBots] = useState<Bot[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    strategy: 'momentum',
    capital: 100000,
    risk_tolerance: 0.5
  })

  const fetchBots = async () => {
    try {
      const res = await axios.get('/api/bot/stats')
      setBots(res.data?.bots || [])
    } catch (err) {
      console.error('Failed to fetch bots:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBots()
  }, [])

  const handleStep = async () => {
    try {
      await axios.post('/api/bot/step')
      fetchBots()
    } catch (err) {
      console.error('Step failed:', err)
    }
  }

  const handleAdd = async () => {
    if (!formData.name.trim()) return
    try {
      await axios.post('/api/bot/add', formData)
      setShowForm(false)
      setFormData({ name: '', strategy: 'momentum', capital: 100000, risk_tolerance: 0.5 })
      fetchBots()
    } catch (err) {
      console.error('Add bot failed:', err)
    }
  }

  const handleRemove = async (name: string) => {
    try {
      await axios.delete(`/api/bot/remove/${encodeURIComponent(name)}`)
      fetchBots()
    } catch (err) {
      console.error('Failed to remove bot:', err)
    }
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('bots.title')}</h2>
          <p className="subtitle">{t('bots.subtitle', 'AI驱动的智能交易代理')}</p>
        </div>
        <div className="card"><div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>🤖 {t('bots.title')}</h2>
        <p className="subtitle">{t('bots.subtitle', 'AI驱动的智能交易代理')}</p>
      </div>

      {/* Stats Overview */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="stat-value">{bots.length}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.activeBots', '活跃交易员')}</div>
        </div>
        <div className="card">
          <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
            {bots.reduce((sum, b) => sum + b.total_pnl, 0).toFixed(2)}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.totalPnl', '总盈亏')}</div>
        </div>
        <div className="card">
          <div className="stat-value">{bots.reduce((sum, b) => sum + b.total_trades, 0).toLocaleString()}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.totalTrades', '总交易次数')}</div>
        </div>
        <div className="card">
          <div className="stat-value">
            {bots.filter(b => b.total_pnl > 0).length}/{bots.length}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.profitable', '盈利交易员')}</div>
        </div>
      </div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="card-title">{t('bots.controls', '控制面板')}</span>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-secondary" onClick={handleStep}>{t('bots.step', '执行一步')}</button>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ {t('bots.addBot', '添加交易员')}</button>
        </div>
      </div>

      {/* Add Bot Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">{t('bots.addBot', '添加交易员')}</span>
            <button className="btn btn-secondary" onClick={() => setShowForm(false)}>✕</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.name', '名称')}</label>
              <input
                type="text"
                className="input-field"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                placeholder={t('bots.enterName', '输入交易员名称')}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.strategy', '策略')}</label>
              <select
                className="input-field"
                value={formData.strategy}
                onChange={e => setFormData({ ...formData, strategy: e.target.value })}
              >
                {Object.entries(STRATEGY_LABELS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.capital', '资金 ($)')}</label>
              <input
                type="number"
                className="input-field"
                value={formData.capital}
                onChange={e => setFormData({ ...formData, capital: Number(e.target.value) })}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.riskTolerance', '风险偏好')}</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={formData.risk_tolerance}
                onChange={e => setFormData({ ...formData, risk_tolerance: Number(e.target.value) })}
                style={{ width: '100%' }}
              />
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{formData.risk_tolerance.toFixed(1)}</span>
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleAdd} style={{ marginTop: 16 }}>{t('bots.addBot', '添加交易员')}</button>
        </div>
      )}

      {/* Bot Cards */}
      {bots.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
          <p style={{ color: 'var(--text-secondary)' }}>{t('bots.noBots', '暂无交易员，点击"+添加交易员"创建第一个AI交易员')}</p>
        </div>
      ) : (
        <div className="grid-3">
          {bots.map((bot, i) => (
            <div key={i} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 12 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16 }}>{bot.name}</h3>
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: 12,
                    fontSize: 11,
                    marginTop: 4,
                    background: `${STRATEGY_COLORS[bot.strategy] || '#6b7280'}22`,
                    color: STRATEGY_COLORS[bot.strategy] || '#6b7280',
                    border: `1px solid ${STRATEGY_COLORS[bot.strategy] || '#6b7280'}44`
                  }}>
                    {STRATEGY_LABELS[bot.strategy] || bot.strategy}
                  </span>
                </div>
                <button
                  onClick={() => handleRemove(bot.name)}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--border-color)',
                    borderRadius: 4,
                    padding: '2px 8px',
                    cursor: 'pointer',
                    color: 'var(--text-secondary)'
                  }}
                >✕</button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.cash', '现金')}</div>
                  <div style={{ fontWeight: 600 }}>${bot.cash.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.pnl', '盈亏')}</div>
                  <div style={{ fontWeight: 600, color: bot.total_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    ${bot.total_pnl.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.trades', '交易次数')}</div>
                  <div style={{ fontWeight: 600 }}>{bot.total_trades}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.risk', '风险')}</div>
                  <div style={{ fontWeight: 600 }}>{(bot.risk_tolerance * 100).toFixed(0)}%</div>
                </div>
              </div>

              {Object.keys(bot.positions).length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>{t('bots.positions', '持仓')}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {Object.entries(bot.positions).slice(0, 5).map(([ticker, qty]) => (
                      <span key={ticker} style={{
                        fontSize: 11,
                        background: 'var(--bg-tertiary)',
                        padding: '2px 6px',
                        borderRadius: 4,
                        color: 'var(--text-primary)'
                      }}>
                        {ticker}: {qty.toFixed(1)}
                      </span>
                    ))}
                    {Object.keys(bot.positions).length > 5 && (
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>+{Object.keys(bot.positions).length - 5}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
