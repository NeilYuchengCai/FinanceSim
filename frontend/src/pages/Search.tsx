import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { t } from '../i18n'

/**
 * 全局搜索页（Wave 2 修复）
 *
 * 契约：GET /api/v1/search?q=&world_id=&limit=
 * -> { assets: [{type,ticker,name,sector}], events: [{type,id,title,type_name}], news: [{type,id,headline,importance}] }
 * 注意：响应是分组对象而非扁平数组（旧实现按数组处理导致永远显示"未找到"）。
 * 无 score 字段：相关度列移除，改展示类型与副标题信息。
 */

interface SearchResultAsset {
  type: 'asset'
  ticker: string
  name?: string
  sector?: string
}

interface SearchResultEvent {
  type: 'event'
  id: string
  title: string
  type_name?: string
}

interface SearchResultNews {
  type: 'news'
  id: string
  headline: string
  importance?: string
}

type SearchResult = SearchResultAsset | SearchResultEvent | SearchResultNews

const TYPE_TAG_CLASS: Record<string, string> = {
  asset: 'tag-blue',
  event: 'tag-orange',
  news: 'tag-purple',
}

function resultTitle(r: SearchResult): string {
  if (r.type === 'asset') return r.name && r.name.trim() ? r.name : r.ticker
  if (r.type === 'event') return r.title
  return r.headline
}

function resultSubtitle(r: SearchResult): string {
  if (r.type === 'asset') return [r.ticker, r.sector].filter(Boolean).join(' · ')
  if (r.type === 'event') return r.type_name ?? '—'
  return r.importance ?? '—'
}

function typeLabel(type: string): string {
  if (type === 'asset') return t('search.assets')
  if (type === 'news') return t('search.news')
  if (type === 'event') return t('search.events')
  return type
}

export default function Search() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (q: string) => {
    if (q.length < 2) {
      setResults([])
      setError(null)
      setSearched(false)
      return
    }
    setSearching(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/search?q=${encodeURIComponent(q)}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      // 响应为分组对象：拍平成统一列表
      const flat: SearchResult[] = [
        ...(Array.isArray(data?.assets) ? data.assets : []),
        ...(Array.isArray(data?.events) ? data.events : []),
        ...(Array.isArray(data?.news) ? data.news : []),
      ]
      setResults(flat)
      setSearched(true)
    } catch {
      // 接口失败与"搜不到"是两回事：失败时明确报错，不显示空结果文案
      setResults([])
      setError(t('common.dataError'))
      setSearched(true)
    } finally {
      setSearching(false)
    }
  }

  const handleRowClick = (r: SearchResult) => {
    if (r.type === 'asset') {
      navigate(`/asset/${encodeURIComponent(r.ticker)}`)
    } else if (r.type === 'news') {
      navigate('/news')
    } else {
      navigate('/timeline')
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('search.title')}</h2>
        <p className="subtitle">{t('search.subtitle')}</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="input-field"
            value={query}
            onChange={(e) => { setQuery(e.target.value); handleSearch(e.target.value) }}
            placeholder={t('search.placeholder')}
            style={{ width: '100%', paddingRight: 100 }}
          />
          <span className="kbd" style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }}>⌘K</span>
        </div>
      </div>

      {searching && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="loading">{t('common.loading')}</div>
        </div>
      )}

      {!searching && error && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="error" style={{ color: 'var(--accent-red)' }}>{error}</div>
        </div>
      )}

      {!searching && !error && results.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('search.results')}</span>
            <span className="tag tag-blue">{results.length} {t('search.items')}</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('search.resultType')}</th>
                <th>{t('search.title')}</th>
                <th>{t('search.detail')}</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr
                  key={r.type === 'asset' ? `asset-${r.ticker}` : `${r.type}-${r.id ?? i}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleRowClick(r)}
                  title={t('search.viewDetail')}
                >
                  <td><span className={`tag ${TYPE_TAG_CLASS[r.type] ?? 'tag-gray'}`}>{typeLabel(r.type)}</span></td>
                  <td>{resultTitle(r)}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{resultSubtitle(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!searching && !error && searched && query.length >= 2 && results.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
          <p style={{ color: 'var(--text-secondary)' }}>{t('search.noResults')}</p>
        </div>
      )}
    </div>
  )
}
