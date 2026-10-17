import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'

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
          axios.get('/api/v1/economy/state'),
          axios.get('/api/v1/news/headlines')
        ])
        setMacro(macroRes.data)
        setNews(newsRes.data || [])
      } catch (err) {
        setError(t('common.dataError'))
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
          <h2>{t('overview.title')}</h2>
          <p className="subtitle">{t('overview.subtitle')}</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('overview.title')}</h2>
          <p className="subtitle">{t('overview.subtitle')}</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  const formatPercent = (v: number) => `${(v * 100).toFixed(2)}%`

  return (
    <div>
      <div className="page-header">
        <h2>{t('overview.title')}</h2>
        <p className="subtitle">{t('overview.subtitle')}</p>
      </div>
      
      <div className="grid-4">
        {macro && (
          <>
          <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.gdp')}</span>
            <span className={`tag ${(macro.gdp_growth || 0) >= 0 ? 'tag-green' : 'tag-red'}`}>
              {(macro.gdp_growth || 0) >= 0 ? '+' : ''}{formatPercent(macro.gdp_growth || 0)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(macro.gdp_growth || 0)}</div>
          <div className="stat-change">{t('overview.annualRate')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.inflation')}</span>
            <span className={`tag ${(macro.inflation || 0) <= 0.02 ? 'tag-green' : 'tag-red'}`}>
              {formatPercent(macro.inflation || 0)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(macro.inflation || 0)}</div>
          <div className="stat-change">{t('overview.inflationTarget')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.unemployment')}</span>
            <span className="tag tag-blue">{formatPercent(macro.unemployment || 0)}</span>
          </div>
          <div className="stat-value">{formatPercent(macro.unemployment || 0)}</div>
          <div className="stat-change">{t('overview.naturalRate')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.interestRate')}</span>
            <span className="tag tag-blue">{formatPercent(macro.interest_rate || 0)}</span>
          </div>
          <div className="stat-value">{formatPercent(macro.interest_rate || 0)}</div>
          <div className="stat-change">{t('overview.policyRate')}</div>
        </div>
        </>
        )}
      </div>
      
      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.marketRegime')}</span>
            <span className="tag tag-purple">{macro?.cycle_phase || 'UNKNOWN'}</span>
          </div>
          <div style={{ padding: 20, textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', fontWeight: 600 }}>{macro?.cycle_phase || '--'}</div>
            <div style={{ color: 'var(--text-secondary)' }}>{t('overview.economicPhase')}: {macro?.cycle_phase || '--'}</div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.economicIndicators')}</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('overview.metric')}</th>
                <th>{t('overview.value')}</th>
                <th>{t('overview.status')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('overview.gdp')}</td>
                <td>{formatPercent(macro?.gdp_growth || 0)}</td>
                <td className={macro?.gdp_growth && macro.gdp_growth >= 0 ? 'positive' : 'negative'}>
                  {macro?.gdp_growth && macro.gdp_growth >= 0 ? '↑ ↑ ' + t('overview.expanding') : '↓ ↓ ' + t('overview.contracting')}
                </td>
              </tr>
              <tr>
                <td>{t('overview.inflation')}</td>
                <td>{formatPercent(macro?.inflation || 0)}</td>
                <td className={(macro?.inflation || 0) <= 0.02 ? 'positive' : 'negative'}>
                  {(macro?.inflation || 0) <= 0.02 ? '✓ ' + t('overview.target') : '⚠ ' + t('overview.high')}
                </td>
              </tr>
              <tr>
                <td>{t('overview.unemployment')}</td>
                <td>{formatPercent(macro?.unemployment || 0)}</td>
                <td className={(macro?.unemployment || 0) <= 0.05 ? 'positive' : 'negative'}>
                  {(macro?.unemployment || 0) <= 0.05 ? '✓ ' + t('overview.healthy') : '⚠ ' + t('overview.elevated')}
                </td>
              </tr>
              <tr>
                <td>{t('overview.interestRate')}</td>
                <td>{formatPercent(macro?.interest_rate || 0)}</td>
                <td><span className="tag tag-blue">{t('overview.current')}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('overview.breakingNews')}</span>
          <span className="tag tag-red">LIVE</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('overview.time')}</th>
              <th>{t('overview.headline')}</th>
              <th>{t('overview.importance')}</th>
              <th>{t('overview.assets')}</th>
            </tr>
          </thead>
          <tbody>
            {news.length > 0 ? (
              news.slice(0, 5).map(item => (
                <tr key={item.id}>
                  <td>{new Date(item.created_at).toLocaleString('zh-CN')}</td>
                  <td>{item.headline}</td>
                  <td>
                    <span className={`tag ${
                      item.importance === 'BREAKING' ? 'tag-red' :
                      item.importance === 'MAJOR' ? 'tag-orange' :
                      item.importance === 'MACRO' ? 'tag-purple' : 'tag-gray'
                    }`}>
                      {item.importance === 'BREAKING' ? t('news.breaking') :
                       item.importance === 'MAJOR' ? t('news.important') :
                       item.importance === 'MACRO' ? t('news.economy') : t('news.normal')}
                    </span>
                  </td>
                  <td>
                    {item.affected_assets?.slice(0, 2).join(', ')}
                    {item.affected_assets?.length > 2 && ` +${item.affected_assets.length - 2}`}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={4} className="loading">{t('common.noData')}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
