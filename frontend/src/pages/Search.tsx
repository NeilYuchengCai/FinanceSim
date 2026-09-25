import { useState } from 'react'

interface SearchResult {
  type: string
  title: string
  score: number
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const handleSearch = async (q: string) => {
    if (q.length < 2) {
      setResults([])
      return
    }
    setSearching(true)
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`)
      const data = await res.json()
      setResults(data || [])
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>全局搜索</h2>
        <p className="subtitle">搜索资产、新闻、事件</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="input-field"
            value={query}
            onChange={(e) => { setQuery(e.target.value); handleSearch(e.target.value) }}
            placeholder="输入关键词搜索..."
            style={{ width: '100%', paddingRight: 100 }}
          />
          <span className="kbd" style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }}>⌘K</span>
        </div>
      </div>

      {searching && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="loading">加载中...</div>
        </div>
      )}

      {!searching && results.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">搜索结果</span>
            <span className="tag tag-blue">{results.length} 条结果</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>标题</th>
                <th>相关度</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r: SearchResult, i: number) => (
                <tr key={i}>
                  <td><span className={`tag ${r.type === 'asset' ? 'tag-blue' : r.type === 'news' ? 'tag-purple' : 'tag-gray'}`}>{r.type}</span></td>
                  <td>{r.title}</td>
                  <td>{(r.score * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!searching && query.length >= 2 && results.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
          <p style={{ color: 'var(--text-secondary)' }}>未找到相关结果</p>
        </div>
      )}
    </div>
  )
}
