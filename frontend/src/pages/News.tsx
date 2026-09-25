import { useState, useEffect } from 'react'
import axios from 'axios'

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

interface DailySummary {
  date: string
  total_news: number
  breaking_count: number
  major_count: number
  summary: string
  highlight?: NewsItem
  market_sentiment: string
  sentiment_score: number
  news_items: NewsItem[]
}

export default function News() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [summary, setSummary] = useState<DailySummary | null>(null)
  const [impact, setImpact] = useState<any>(null)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch news
        const params: any = { limit: 50 }
        if (filter !== 'all') params.category = filter
        const newsRes = await axios.get('/api/news', { params })
        setNews(newsRes.data || [])
        
        // Fetch daily summary
        const summaryRes = await axios.get('/api/news/daily-summary/0')
        setSummary(summaryRes.data)
        
        // Fetch impact summary
        const impactRes = await axios.get('/api/news/impact-summary')
        setImpact(impactRes.data)
      } catch (err) {
        setError('Failed to load news')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [filter])

  const getSentimentColor = (s: number) => {
    if (s > 0.3) return 'positive'
    if (s < -0.3) return 'negative'
    return ''
  }

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

  const getSentimentBadge = (sentiment: string, score: number) => {
    const colors: Record<string, string> = {
      Bullish: 'tag-green',
      Bearish: 'tag-red',
      Neutral: 'tag-gray'
    }
    return (
      <span className={`tag ${colors[sentiment] || 'tag-gray'}`}>
        {sentiment} {score !== undefined && Math.abs(score) > 0.01 && `(${score.toFixed(2)})`}
      </span>
    )
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>News</h2>
          <p className="subtitle">Market news and events</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading news...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>News</h2>
          <p className="subtitle">Market news and events</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>News</h2>
        <p className="subtitle">Market news and events</p>
      </div>

      {/* Breaking News Banner */}
      {impact && impact.breaking_count > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(248,81,73,0.15) 0%, rgba(248,81,73,0.05) 100%)',
          border: '1px solid var(--accent-red)',
          borderRadius: '8px',
          padding: '16px 20px',
          marginBottom: 20,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: 20 }}>🔴</span>
            <span style={{ fontWeight: 600, color: 'var(--accent-red)' }}>BREAKING NEWS</span>
            <span className="kbd">{impact.breaking_count} items</span>
          </div>
          <p style={{ margin: 0, color: 'var(--text-primary)' }}>{impact.impact_summary}</p>
        </div>
      )}

      {/* Daily Summary Card */}
      {summary && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">Daily Summary</span>
            {getSentimentBadge(summary.market_sentiment, summary.sentiment_score)}
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.6 }}>
            {summary.summary}
          </p>
          {summary.highlight && (
            <div style={{
              padding: '12px 16px',
              background: 'var(--bg-tertiary)',
              borderRadius: '6px',
              borderLeft: '3px solid var(--accent-yellow)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span className={`tag ${getImportanceTag(summary.highlight.importance)}`}>
                  {summary.highlight.importance}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {new Date(summary.highlight.created_at).toLocaleString()}
                </span>
              </div>
              <div style={{ fontWeight: 500 }}>{summary.highlight.headline}</div>
              <div style={{ marginTop: 4, fontSize: 13, color: 'var(--text-secondary)' }}>
                Sentiment: <span className={getSentimentColor(summary.highlight.sentiment)}>{summary.highlight.sentiment.toFixed(2)}</span>
              </div>
            </div>
          )}
          <div style={{ marginTop: 12, display: 'flex', gap: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
            <span>📰 {summary.total_news} news items</span>
            <span style={{ color: 'var(--accent-red)' }}>⚠️ {summary.breaking_count} breaking</span>
            <span style={{ color: 'var(--accent-yellow)' }}>📌 {summary.major_count} major</span>
          </div>
        </div>
      )}

      {/* News Filter and List */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">All News</span>
          <select
            className="input-field"
            style={{ width: 'auto' }}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All</option>
            <option value="BREAKING">Breaking</option>
            <option value="MAJOR">Major</option>
            <option value="IMPORTANT">Important</option>
            <option value="MARKET">Market</option>
            <option value="COMPANY">Company</option>
            <option value="MACRO">Macro</option>
          </select>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Headline</th>
              <th>Importance</th>
              <th>Sentiment</th>
              <th>Assets</th>
            </tr>
          </thead>
          <tbody>
            {news.length > 0 ? (
              news.map(item => (
                <tr key={item.id}>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                  <td>{item.headline}</td>
                  <td>
                    <span className={`tag ${getImportanceTag(item.importance)}`}>
                      {item.importance}
                    </span>
                  </td>
                  <td className={getSentimentColor(item.sentiment || 0)}>
                    {(item.sentiment || 0).toFixed(2)}
                  </td>
                  <td>
                    {item.affected_assets?.slice(0, 2).join(', ')}
                    {item.affected_assets?.length > 2 && ` +${item.affected_assets.length - 2}`}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={5} className="loading">No news available</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
