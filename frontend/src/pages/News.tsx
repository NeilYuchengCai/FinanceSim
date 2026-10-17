import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'

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
}

export default function News() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: any = { limit: 50 }
        if (filter !== 'all') params.category = filter
        const newsRes = await axios.get('/api/v1/news', { params })
        setNews(newsRes.data || [])
      } catch (err) {
        setError(t('common.networkError'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [filter])

  const getImportanceTag = (imp: string) => {
    const map: Record<string, string> = {
      BREAKING: 'tag-red',
      MAJOR: 'tag-orange',
      IMPORTANT: 'tag-blue',
      MARKET: 'tag-gray',
      COMPANY: 'tag-gray',
      MACRO: 'tag-purple'
    }
    return map[imp] || 'tag-gray'
  }

  const getImportanceLabel = (imp: string) => {
    const map: Record<string, string> = {
      BREAKING: t('news.breaking'),
      MAJOR: t('news.important'),
      IMPORTANT: t('news.important'),
      MARKET: t('news.market'),
      COMPANY: t('news.company'),
      MACRO: t('news.economy')
    }
    return map[imp] || imp
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('news.title')}</h2>
          <p className="subtitle">{t('news.subtitle')}</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('news.title')}</h2>
          <p className="subtitle">{t('news.subtitle')}</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('news.title')}</h2>
        <p className="subtitle">{t('news.subtitle')}</p>
      </div>

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
            <option value="BREAKING">{t('news.breaking')}</option>
            <option value="MAJOR">{t('news.important')}</option>
            <option value="IMPORTANT">{t('news.important')}</option>
            <option value="MARKET">{t('news.market')}</option>
            <option value="COMPANY">{t('news.company')}</option>
            <option value="MACRO">{t('news.economy')}</option>
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
              news.map(item => (
                <tr key={item.id}>
                  <td>{new Date(item.created_at).toLocaleString('zh-CN')}</td>
                  <td>{item.headline}</td>
                  <td>
                    <span className={`tag ${getImportanceTag(item.importance)}`}>
                      {getImportanceLabel(item.importance)}
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
              ))
            ) : (
              <tr><td colSpan={5} className="loading">{t('common.noData')}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
