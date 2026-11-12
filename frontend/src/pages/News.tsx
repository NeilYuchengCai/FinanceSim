import { useState, useEffect, Fragment } from 'react'
import axios from 'axios'
import { t, useLanguage } from '../i18n'

interface NewsItem {
  id: string
  headline: string
  body: string
  importance: string
  sentiment: number
  category: string
  affected_assets: string[]
  created_at: string
  is_read: boolean
  source?: string
  data_source?: string
}

// 后端 NewsImportance 枚举实际值（news_engine.py）：BREAKING/MAJOR/MARKET/COMPANY/MACRO/MINOR
const IMPORTANCE_VALUES = ['BREAKING', 'MAJOR', 'MARKET', 'COMPANY', 'MACRO', 'MINOR'] as const

const IMPORTANCE_TAG_CLASS: Record<string, string> = {
  BREAKING: 'tag-red',
  MAJOR: 'tag-orange',
  MARKET: 'tag-blue',
  COMPANY: 'tag-gray',
  MACRO: 'tag-purple',
  MINOR: 'tag-gray',
}

function importanceTagClass(imp: string): string {
  return IMPORTANCE_TAG_CLASS[imp] || 'tag-gray'
}

function importanceLabel(imp: string): string {
  const map: Record<string, string> = {
    BREAKING: t('news.breaking'),
    MAJOR: t('news.major'),
    MARKET: t('news.market'),
    COMPANY: t('news.company'),
    MACRO: t('news.economy'),
    MINOR: t('news.minor'),
  }
  return map[imp] || imp
}

export default function News() {
  const { language } = useLanguage()
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: Record<string, string | number> = { limit: 50 }
        if (filter !== 'all') params.importance = filter
        const newsRes = await axios.get('/api/v1/news', { params })
        setNews(Array.isArray(newsRes.data) ? newsRes.data : [])
        setError(null)
      } catch {
        setError(t('common.networkError'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [filter])

  const formatTime = (value: string): string => {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '—'
    return date.toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')
  }

  const header = (
    <div className="page-header">
      <h2>{t('news.title')}</h2>
      <p className="subtitle">{t('news.subtitle')}</p>
    </div>
  )

  if (loading) {
    return (
      <div>
        {header}
        <div className="card"><div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        {header}
        <div className="card"><div className="error" style={{ padding: 40 }}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      {header}

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('news.allNews')}</span>
          <select
            className="input-field"
            style={{ width: 'auto' }}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">{t('common.all')}</option>
            {IMPORTANCE_VALUES.map(v => (
              <option key={v} value={v}>{importanceLabel(v)}</option>
            ))}
          </select>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>{t('overview.time')}</th>
              <th>{t('overview.headline')}</th>
              <th>{t('overview.importance')}</th>
              <th>{t('news.sentiment')}</th>
              <th>{t('overview.assets')}</th>
            </tr>
          </thead>
          <tbody>
            {news.length > 0 ? (
              news.map(item => {
                const expanded = expandedId === item.id
                return (
                  <Fragment key={item.id}>
                    <tr
                      onClick={() => setExpandedId(expanded ? null : item.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>{formatTime(item.created_at)}</td>
                      <td>{item.headline}</td>
                      <td>
                        <span className={`tag ${importanceTagClass(item.importance)}`}>
                          {importanceLabel(item.importance)}
                        </span>
                      </td>
                      <td className={item.sentiment > 0.3 ? 'positive' : item.sentiment < -0.3 ? 'negative' : ''}>
                        {item.sentiment.toFixed(2)}
                      </td>
                      <td>
                        {item.affected_assets?.slice(0, 2).join(', ')}
                        {item.affected_assets?.length > 2 && ` +${item.affected_assets.length - 2}`}
                      </td>
                    </tr>
                    {expanded && (
                      <tr>
                        <td colSpan={5} style={{ background: 'var(--bg-secondary)', whiteSpace: 'pre-wrap' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '8px 0' }}>
                            <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                              {t('news.category')}: {item.category || '—'} · {t('news.sentiment')}: {item.sentiment.toFixed(2)}
                            </div>
                            <div>{item.body || t('news.noBody')}</div>
                            {item.affected_assets && item.affected_assets.length > 0 && (
                              <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                                {t('news.affectedAssets')}: {item.affected_assets.join(', ')}
                              </div>
                            )}
                            {(item.source || item.data_source) && (
                              <div style={{ color: 'var(--text-secondary)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                                <span>{t('news.source')}: {item.source || '—'}</span>
                                {item.data_source && (
                                  <span
                                    className={`tag ${item.data_source === 'LIVE' ? 'tag-green' : 'tag-gray'}`}
                                    style={{ fontSize: 11 }}
                                  >
                                    {item.data_source === 'LIVE' ? t('news.realExternal') : t('news.simulated')}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })
            ) : (
              <tr><td colSpan={5} className="loading">{t('common.noData')}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
