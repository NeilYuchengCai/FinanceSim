import { useState, useEffect } from 'react'
import axios from 'axios'

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

interface CategorySummary {
  count: number
  avg_change_pct: number
  items: Array<{
    ticker: string
    price: number
    change_pct: number
  }>
}

interface MarketSummary {
  total: number
  categories: Record<string, CategorySummary>
  top_gainers: Commodity[]
  top_losers: Commodity[]
}

const CATEGORY_COLORS: Record<string, string> = {
  ENERGY: '#f59e0b',
  METAL: '#6b7280',
  AGRICULTURE: '#22c55e',
  PRECIOUS_METAL: '#fbbf24',
}

export default function Commodities() {
  const [commodities, setCommodities] = useState<Commodity[]>([])
  const [summary, setSummary] = useState<MarketSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [commsRes, summaryRes] = await Promise.all([
          axios.get('/api/commodities'),
          axios.get('/api/commodities/summary'),
        ])
        setCommodities(commsRes.data || [])
        setSummary(summaryRes.data || null)
      } catch (err) {
        setError('Failed to load commodity data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const formatPrice = (price: number) => {
    if (price > 100) return `$${price.toFixed(2)}`
    if (price > 10) return `$${price.toFixed(3)}`
    return `$${price.toFixed(4)}`
  }

  const formatChange = (pct: number) => {
    const sign = pct >= 0 ? '+' : ''
    return `${sign}${(pct * 100).toFixed(3)}%`
  }

  const formatVolume = (v: number) => {
    if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`
    if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`
    if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`
    return v.toString()
  }

  const filteredCommodities = selectedCategory === 'ALL'
    ? commodities
    : commodities.filter(c => c.category === selectedCategory)

  const categories = ['ALL', 'ENERGY', 'METAL', 'AGRICULTURE', 'PRECIOUS_METAL']

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>Commodities</h2>
          <p className="subtitle">Global commodity markets</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading commodity data...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>Commodities</h2>
          <p className="subtitle">Global commodity markets</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>Commodities</h2>
        <p className="subtitle">Global commodity markets · <span className="data-source simulated">SIMULATED</span></p>
      </div>

      {/* Category Filter */}
      <div className="card" style={{marginBottom: 16}}>
        <div className="card-header">
          <span className="card-title">Categories</span>
        </div>
        <div style={{display: 'flex', gap: 8, flexWrap: 'wrap'}}>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: `1px solid ${selectedCategory === cat ? (CATEGORY_COLORS[cat] || '#3b82f6') : 'var(--border-color)'}`,
                background: selectedCategory === cat ? `${CATEGORY_COLORS[cat] || '#3b82f6'}22` : 'var(--bg-secondary)',
                color: selectedCategory === cat ? (CATEGORY_COLORS[cat] || '#3b82f6') : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: selectedCategory === cat ? 600 : 400,
              }}
            >
              {cat === 'ALL' ? 'All' : cat.replace('_', ' ')}
              <span style={{marginLeft: 6, opacity: 0.7}}>
                {cat === 'ALL' ? summary?.total : summary?.categories[cat]?.count || 0}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Category Summary Cards */}
      {summary && Object.entries(summary.categories).map(([cat, data]) => (
        <div key={cat} className="card" style={{marginBottom: 16}}>
          <div className="card-header">
            <span className="card-title" style={{color: CATEGORY_COLORS[cat]}}>
              {cat.replace('_', ' ')}
            </span>
            <span className={`badge ${data.avg_change_pct >= 0 ? 'green' : 'red'}`}>
              {formatChange(data.avg_change_pct)}
            </span>
          </div>
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12}}>
            {data.items.map(item => (
              <div key={item.ticker} style={{padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: 6}}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 4}}>
                  <strong>{item.ticker}</strong>
                  <span className={item.change_pct >= 0 ? 'positive' : 'negative'}>
                    {(item.change_pct >= 0 ? '+' : '') + (item.change_pct * 100).toFixed(3)}%
                  </span>
                </div>
                <div style={{fontSize: 18, fontWeight: 600}}>{formatPrice(item.price)}</div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Full Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">All Commodities</span>
          <span className="tag tag-blue">{filteredCommodities.length} items</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Category</th>
              <th>Price</th>
              <th>Baseline</th>
              <th>Volatility</th>
              <th>Supply</th>
              <th>Demand</th>
              <th>Inventory</th>
              <th>Seasonality</th>
            </tr>
          </thead>
          <tbody>
            {filteredCommodities.map(commodity => (
              <tr key={commodity.ticker}>
                <td><strong>{commodity.ticker}</strong></td>
                <td>{commodity.name}</td>
                <td>
                  <span style={{
                    color: CATEGORY_COLORS[commodity.category],
                    fontWeight: 500
                  }}>
                    {commodity.category}
                  </span>
                </td>
                <td>{formatPrice(commodity.current_price)}</td>
                <td style={{opacity: 0.6}}>{formatPrice(commodity.baseline_price)}</td>
                <td>{(commodity.volatility * 100).toFixed(1)}%</td>
                <td>{formatVolume(commodity.supply)}</td>
                <td>{formatVolume(commodity.demand)}</td>
                <td>{formatVolume(commodity.inventory)}</td>
                <td>{commodity.seasonality_factor.toFixed(2)}x</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
