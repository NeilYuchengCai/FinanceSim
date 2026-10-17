import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { useToast } from '../components/Toast'

interface Bot {
  name: string
  strategy: string
  cash: number
  positions: Record<string, number>
  total_trades: number
  total_pnl: number
  risk_tolerance: number
}

interface BotTrade {
  id?: string
  ticker?: string
  side?: string
  quantity?: number
  price?: number | null
  created_at?: string
  timestamp?: string
}

const STRATEGY_LABELS: Record<string, string> = {
  momentum: t('bots.momentum'),
  mean_reversion: t('bots.meanReversion'),
  market_making: t('bots.marketMaking'),
  random: t('bots.random'),
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

function formatTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN')
}

export default function Bots() {
  const toast = useToast()
  const [bots, setBots] = useState<Bot[]>([])
  const [botTrades, setBotTrades] = useState<BotTrade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    strategy: 'momentum',
    capital: 100000,
    risk_tolerance: 0.5
  })

  const fetchBots = useCallback(async () => {
    try {
      const [statsRes, tradesRes] = await Promise.all([
        axios.get('/api/v1/bots/stats'),
        axios.get('/api/v1/bots/trades', { params: { limit: 50 } }),
      ])
      setBots(statsRes.data?.bots || [])
      setBotTrades(Array.isArray(tradesRes.data) ? tradesRes.data : [])
      setError(null)
    } catch (err) {
      // 失败不再是静默空态：明确报错，用户可重试
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBots()
  }, [fetchBots])

  const handleStep = async () => {
    try {
      await axios.post('/api/v1/bots/step')
      await fetchBots()
      toast.success(t('toast.botStepSuccess'))
    } catch (err) {
      setError(t('simulation.actionFailed'))
      toast.error(t('toast.botStepFailed'))
    }
  }

  const handleAdd = async () => {
    if (!formData.name.trim()) return
    try {
      await axios.post('/api/v1/bots/add', formData)
      setShowForm(false)
      setFormData({ name: '', strategy: 'momentum', capital: 100000, risk_tolerance: 0.5 })
      await fetchBots()
      toast.success(t('toast.botAddSuccess'))
    } catch (err) {
      setError(t('toast.botAddFailed'))
      toast.error(t('toast.botAddFailed'))
    }
  }

  const handleRemove = async (name: string) => {
    try {
      await axios.delete(`/api/v1/bots/remove/${encodeURIComponent(name)}`)
      await fetchBots()
      toast.success(t('toast.botRemoveSuccess'))
    } catch (err) {
      setError(t('toast.botRemoveFailed'))
      toast.error(t('toast.botRemoveFailed'))
    }
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('bots.title')}</h2>
          <p className="subtitle">{t('bots.subtitle')}</p>
        </div>
        <div className="card"><div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>🤖 {t('bots.title')}</h2>
        <p className="subtitle">{t('bots.subtitle')}</p>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--accent-red)' }}>
          <div className="error" style={{ padding: 16, color: 'var(--accent-red)' }}>{error}</div>
          <button className="btn" style={{ marginTop: 12 }} onClick={fetchBots}>
            {t('common.retry')}
          </button>
        </div>
      )}

      {/* Stats Overview */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="stat-value">{bots.length}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.activeBots')}</div>
        </div>
        <div className="card">
          <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
            {bots.reduce((sum, b) => sum + b.total_pnl, 0).toFixed(2)}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.totalPnl')}</div>
        </div>
        <div className="card">
          <div className="stat-value">{bots.reduce((sum, b) => sum + b.total_trades, 0).toLocaleString()}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.totalTrades')}</div>
        </div>
        <div className="card">
          <div className="stat-value">
            {bots.filter(b => b.total_pnl > 0).length}/{bots.length}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('bots.profitable')}</div>
        </div>
      </div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="card-title">{t('bots.controls')}</span>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-secondary" onClick={handleStep}>{t('bots.step')}</button>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ {t('bots.addBot')}</button>
        </div>
      </div>

      {/* Add Bot Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">{t('bots.addBot')}</span>
            <button className="btn btn-secondary" onClick={() => setShowForm(false)}>✕</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.name')}</label>
              <input
                type="text"
                className="input-field"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                placeholder={t('bots.enterName')}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.strategy')}</label>
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
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.capital')}</label>
              <input
                type="number"
                className="input-field"
                value={formData.capital}
                onChange={e => setFormData({ ...formData, capital: Number(e.target.value) })}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{t('bots.riskTolerance')}</label>
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
          <button className="btn btn-primary" onClick={handleAdd} style={{ marginTop: 16 }}>{t('bots.addBot')}</button>
        </div>
      )}

      {/* Bot Cards */}
      {bots.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
          <p style={{ color: 'var(--text-secondary)' }}>{t('bots.noBots')}</p>
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
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.cash')}</div>
                  <div style={{ fontWeight: 600 }}>${bot.cash.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.pnl')}</div>
                  <div style={{ fontWeight: 600, color: bot.total_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    ${bot.total_pnl.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.trades')}</div>
                  <div style={{ fontWeight: 600 }}>{bot.total_trades}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('bots.risk')}</div>
                  <div style={{ fontWeight: 600 }}>{(bot.risk_tolerance * 100).toFixed(0)}%</div>
                </div>
              </div>

              {Object.keys(bot.positions).length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>{t('bots.positions')}</div>
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

      {/* 成交流水 */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('bots.recentTrades')}</span>
          <button className="btn btn-sm" onClick={fetchBots}>{t('common.refresh')}</button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('orders.time')}</th>
              <th>{t('equities.ticker')}</th>
              <th>{t('orders.direction')}</th>
              <th>{t('orders.quantity')}</th>
              <th>{t('orders.price')}</th>
            </tr>
          </thead>
          <tbody>
            {botTrades.length > 0 ? (
              botTrades.slice(0, 20).map((trade, i) => (
                <tr key={trade.id ?? i}>
                  <td>{formatTime(trade.created_at ?? trade.timestamp)}</td>
                  <td><strong>{trade.ticker ?? '—'}</strong></td>
                  <td className={trade.side === 'BUY' ? 'cn-up' : trade.side === 'SELL' ? 'cn-down' : undefined}>
                    {trade.side === 'BUY' ? t('orders.buy') : trade.side === 'SELL' ? t('orders.sell') : '—'}
                  </td>
                  <td>{trade.quantity ?? '—'}</td>
                  <td>{trade.price != null ? `$${trade.price.toFixed(2)}` : '—'}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={5} className="loading">{t('bots.noTrades')}</td>
            </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
