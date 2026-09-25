import { useState } from 'react'
import axios from 'axios'

interface SearchResult {
  type: string
  ticker?: string
  name?: string
  sector?: string
  id?: string
  title?: string
  headline?: string
  importance?: string
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    
    setLoading(true)
    setSearched(true)
    try {
      const res = await axios.get(`/api/search?q=${encodeURIComponent(query)}`)
      setResults([
        ...res.data.assets.map((a: any) => ({ ...a, type: 'asset' })),
        ...res.data.events.map((e: any) => ({ ...e, type: 'event' })),
        ...res.data.news.map((n: any) => ({ ...n, type: 'news' }))
      ])
    } catch (err) {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const getIcon = (type: string) => {
    switch(type) {
      case 'asset': return '📈'
      case 'event': return '📰'
      case 'news': return '📋'
      default: return '🔍'
    }
  }

  const getTypeColor = (type: string) => {
    switch(type) {
      case 'asset': return 'tag-blue'
      case 'event': return 'tag-orange'
      case 'news': return 'tag-purple'
      default: return 'tag-gray'
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Search</h2>
        <p className="subtitle">Global search across markets</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Search</span>
        </div>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 12 }}>
          <input
            type="text"
            className="input-field"
            placeholder="Search by ticker, company, event..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {searched && (
          <div style={{ marginTop: 20 }}>
            {results.length > 0 ? (
              <>
                <div style={{ marginBottom: 12, color: 'var(--text-secondary)' }}>
                  Found {results.length} results
                </div>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Name/Headline</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((item, i) => (
                      <tr key={i}>
                        <td>
                          <span className={`tag ${getTypeColor(item.type)}`}>
                            {getIcon(item.type)} {item.type.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          {item.type === 'asset' && <strong>{item.ticker}</strong>}
                          {item.type === 'event' && <strong>{item.title}</strong>}
                          {item.type === 'news' && <strong>{item.headline}</strong>}
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>
                          {item.type === 'asset' && item.sector}
                          {item.type === 'news' && item.importance}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-secondary)' }}>
                No results found
              </div>
            )}
          </div>
        )}

        {!searched && (
          <div style={{ marginTop: 20, color: 'var(--text-secondary)', textAlign: 'center', padding: 20 }}>
            Enter a search term to find assets, events, or news...
          </div>
        )}
      </div>
    </div>
  )
}
