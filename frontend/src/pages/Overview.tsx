import { useState, useEffect } from 'react'
import axios from 'axios'

interface NewsItem {
  id: string
  headline: string
  importance: string
  affected_assets: string[]
  created_at: string
}

interface MacroState {
  gdp_growth: number
  inflation: number
  unemployment: number
  interest_rate: number
  cycle_phase: string
}

export default function Overview() {
  const [macro, setMacro] = useState<MacroState | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [macroRes, newsRes] = await Promise.all([
          axios.get('/api/economy/state'),
          axios.get('/api/news/headlines')
        ])
        setMacro(macroRes.data)
        setNews(newsRes.data || [])
      } catch (err) {
        setError('Failed to load overview data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>Market Overview</h2>
          <p className="subtitle">Global financial markets at a glance</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading market data...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>Market Overview</h2>
          <p className="subtitle">Global financial markets at a glance</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  const formatPercent = (v: number) => `${(v * 100).toFixed(2)}%`

  return (
    <div>
      <div className="page-header">
        <h2>Market Overview</h2>
        <p className="subtitle">Global financial markets at a glance</p>
      </div>
      
      <div className="grid-4">
        {macro && (
          <>
          <div className="card">
          <div className="card-header">
            <span className="card-title">GDP Growth</span>
            <span className={`tag ${(macro.gdp_growth || 0) >= 0 ? 'tag-green' : 'tag-red'}`}>
              {(macro.gdp_growth || 0) >= 0 ? '+' : ''}{formatPercent(macro.gdp_growth || 0)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(macro.gdp_growth || 0)}</div>
          <div className="stat-change">Annual rate</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Inflation</span>
            <span className={`tag ${(macro.inflation || 0) <= 0.02 ? 'tag-green' : 'tag-red'}`}>
              {formatPercent(macro.inflation || 0)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(macro.inflation || 0)}</div>
          <div className="stat-change">Target: 2.0%</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Unemployment</span>
            <span className="tag tag-blue">{formatPercent(macro.unemployment || 0)}</span>
          </div>
          <div className="stat-value">{formatPercent(macro.unemployment || 0)}</div>
          <div className="stat-change">Natural rate: 5.0%</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Interest Rate</span>
            <span className="tag tag-blue">{formatPercent(macro.interest_rate || 0)}</span>
          </div>
          <div className="stat-value">{formatPercent(macro.interest_rate || 0)}</div>
          <div className="stat-change">Policy rate</div>
        </div>
        </>
        )}
      </div>
      
      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Market Regime</span>
            <span className="tag tag-purple">{macro?.cycle_phase || 'UNKNOWN'}</span>
          </div>
          <div style={{ padding: 20, textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', fontWeight: 600 }}>{macro?.cycle_phase || '--'}</div>
            <div style={{ color: 'var(--text-secondary)' }}>Economic Phase: {macro?.cycle_phase || 'Unknown'}</div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-header">
            <span className="card-title">Economic Indicators</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>GDP Growth</td>
                <td>{formatPercent(macro?.gdp_growth || 0)}</td>
                <td className={macro?.gdp_growth && macro.gdp_growth >= 0 ? 'positive' : 'negative'}>
                  {macro?.gdp_growth && macro.gdp_growth >= 0 ? '↑ Expanding' : '↓ Contracting'}
                </td>
              </tr>
              <tr>
                <td>Inflation</td>
                <td>{formatPercent(macro?.inflation || 0)}</td>
                <td className={(macro?.inflation || 0) <= 0.02 ? 'positive' : 'negative'}>
                  {(macro?.inflation || 0) <= 0.02 ? '✓ Target' : '⚠ High'}
                </td>
              </tr>
              <tr>
                <td>Unemployment</td>
                <td>{formatPercent(macro?.unemployment || 0)}</td>
                <td className={(macro?.unemployment || 0) <= 0.05 ? 'positive' : 'negative'}>
                  {(macro?.unemployment || 0) <= 0.05 ? '✓ Healthy' : '⚠ Elevated'}
                </td>
              </tr>
              <tr>
                <td>Interest Rate</td>
                <td>{formatPercent(macro?.interest_rate || 0)}</td>
                <td><span className="tag tag-blue">Current</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">Breaking News</span>
          <span className="tag tag-red">LIVE</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Headline</th>
              <th>Importance</th>
              <th>Assets</th>
            </tr>
          </thead>
          <tbody>
            {news.length > 0 ? (
              news.slice(0, 5).map(item => (
                <tr key={item.id}>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                  <td>{item.headline}</td>
                  <td>
                    <span className={`tag ${
                      item.importance === 'BREAKING' ? 'tag-red' :
                      item.importance === 'MAJOR' ? 'tag-orange' :
                      item.importance === 'MACRO' ? 'tag-purple' : 'tag-gray'
                    }`}>
                      {item.importance}
                    </span>
                  </td>
                  <td>
                    {item.affected_assets?.slice(0, 2).join(', ')}
                    {item.affected_assets?.length > 2 && ` +${item.affected_assets.length - 2}`}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={4} className="loading">No breaking news</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
