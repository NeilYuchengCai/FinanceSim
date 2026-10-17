import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'

interface Commodity {
  ticker: string
  name: string
  category: string
  subcategory: string
  current_price: number
  baseline_price: number
  volatility: number
  contract_size: number
  tick_size: number
  seasonality_factor: number
  supply: number
  demand: number
  inventory: number
  last_update: string
}

const CATEGORY_NAMES: Record<string, string> = {
  ALL: t('commodities.all'),
  ENERGY: t('commodities.energy'),
  METAL: t('commodities.metals'),
  AGRICULTURE: t('commodities.agriculture'),
  PRECIOUS_METAL: t('commodities.precious'),
}

export default function Commodities() {
  const { worldId } = useCurrentWorld()
  const navigate = useNavigate()
  const [commodities, setCommodities] = useState<Commodity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    const fetchCommodities = async () => {
      try {
        const res = await axios.get(`/api/v1/commodities?world_id=${worldId}`)
        setCommodities(res.data)
      } catch (err) {
        setError(t('common.dataError'))
      } finally {
        setLoading(false)
      }
    }
    fetchCommodities()
  }, [worldId])

  const filtered = filter === 'ALL' ? commodities : commodities.filter(c => c.category === filter)
  const categories = [...new Set(commodities.map(c => c.category))]

  const formatPrice = (p: number) => p.toFixed(2)
  // 真实涨跌幅 = 现价相对基准价的偏离，由引擎演化得出。
  // 此前用 Math.random() 伪造，违反"禁止硬编码假数据"原则。
  const changePct = (c: Commodity) => {
    if (!c.baseline_price) return null
    return (c.current_price / c.baseline_price - 1) * 100
  }
  const formatChange = (c: Commodity) => {
    const chg = changePct(c)
    if (chg === null || Number.isNaN(chg)) return '--'
    return `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`
  }
  const changeClass = (c: Commodity) => {
    const chg = changePct(c)
    if (chg === null || Number.isNaN(chg)) return ''
    return chg >= 0 ? 'positive' : 'negative'
  }
  const formatVolume = (v: number) => {
    if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`
    if (v >= 1000) return `${(v / 1000).toFixed(0)}K`
    return v.toString()
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('commodities.title')}</h2>
          <p className="subtitle">{t('commodities.subtitle')} · <span className="data-source simulated">{t('commodities.simulated')}</span></p>
        </div>
        <div className="card"><div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('commodities.title')}</h2>
          <p className="subtitle">{t('commodities.subtitle')} · <span className="data-source simulated">{t('commodities.simulated')}</span></p>
        </div>
        <div className="card"><div className="error" style={{ padding: 40 }}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('commodities.title')}</h2>
        <p className="subtitle">{t('commodities.subtitle')} · {commodities.length} commodities</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('commodities.categories')}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            onClick={() => setFilter('ALL')}
            style={{
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid var(--border-color)',
              background: filter === 'ALL' ? 'var(--accent-color)' : 'var(--bg-secondary)',
              color: filter === 'ALL' ? 'white' : 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {t('commodities.all')}
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: '1px solid var(--border-color)',
                background: filter === cat ? 'var(--accent-color)' : 'var(--bg-secondary)',
                color: filter === cat ? 'white' : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {CATEGORY_NAMES[cat] || cat}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('commodities.allCommodities')}</span>
          <span className="tag tag-blue">LIVE</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('commodities.category')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('equities.change')}</th>
              <th>{t('commodities.volatility')}</th>
              <th>{t('commodities.supplyDemand')}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(comm => (
              <tr
                key={comm.ticker}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/asset/${encodeURIComponent(comm.ticker)}`)}
                title={t('assetDetail.viewDetail')}
              >
                <td>{comm.ticker}</td>
                <td>{comm.name}</td>
                <td>
                  <span className={`tag ${
                    comm.category === 'ENERGY' ? 'tag-orange' :
                    comm.category === 'PRECIOUS_METAL' ? 'tag-yellow' :
                    comm.category === 'METAL' ? 'tag-gray' : 'tag-green'
                  }`}>
                    {comm.category}
                  </span>
                </td>
                <td>${formatPrice(comm.current_price)}</td>
                <td className={changeClass(comm)}>{formatChange(comm)}</td>
                <td>{(comm.volatility * 100).toFixed(1)}%</td>
                <td>
                  <span className={comm.supply >= comm.demand ? 'positive' : 'negative'}>
                    {comm.supply >= comm.demand ? '↑' : '↓'} {formatVolume(Math.abs(comm.supply - comm.demand))}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
