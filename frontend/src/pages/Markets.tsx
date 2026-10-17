import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { t } from '../i18n'
import { LivePrice, LiveChange } from '../components/LiveQuote'
import { usePriceStreamStatus, usePriceStreamPaused } from '../hooks/usePriceStream'
import { useCurrentWorld } from '../hooks/useCurrentWorld'

interface Quote {
  ticker: string
  name: string
  price: number
  change_pct: number
}

interface ActiveQuote extends Quote {
  volume: number
}

interface SectorRow {
  sector: string
  count: number
  avg_change_pct: number
  advancing: number
  declining: number
}

interface Breadth {
  total_tracked: number
  advancing: number
  declining: number
  unchanged: number
  advancers_pct: number
  decliners_pct: number
  advance_decline_ratio: number | null
  advance_decline_line: number
  new_highs: number
  new_lows: number
  avg_change_pct: number
  distribution: Record<string, number>
  sectors: SectorRow[]
  indices: Quote[]
  gainers: Quote[]
  losers: Quote[]
  most_active: ActiveQuote[]
}

// 涨跌幅分布桶，顺序固定由负到正
const DIST_BUCKETS: Array<[string, string]> = [
  ['below_-5', '< -5%'],
  ['-5_to_-2', '-5% ~ -2%'],
  ['-2_to_-0.5', '-2% ~ -0.5%'],
  ['-0.5_to_0.5', '-0.5% ~ 0.5%'],
  ['0.5_to_2', '0.5% ~ 2%'],
  ['2_to_5', '2% ~ 5%'],
  ['above_5', '> 5%'],
]

// 首页置顶展示的核心指数，缺失时由后端返回的其他指数补齐
const FEATURED_INDEX = ['SPX', 'NDX', 'DJI', 'N225']

const pct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`

function dirClass(v: number) {
  if (v > 0) return 'positive'
  if (v < 0) return 'negative'
  return ''
}

const rowClickStyle = { cursor: 'pointer' }

function QuoteTable({ rows, valueLabel }: { rows: Quote[]; valueLabel: string }) {
  const navigate = useNavigate()
  if (!rows.length) return <div className="loading">{t('common.noData')}</div>
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>{t('markets.code')}</th>
          <th>{valueLabel}</th>
          <th>{t('markets.change')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr
            key={r.ticker}
            style={rowClickStyle}
            onClick={() => navigate(`/asset/${encodeURIComponent(r.ticker)}`)}
            title={t('assetDetail.viewDetail')}
          >
            <td>{r.ticker}</td>
            <td>
              <LivePrice ticker={r.ticker} fallback={r.price} format={(v) => v.toLocaleString()} />
            </td>
            <td>
              <LiveChange ticker={r.ticker} fallback={r.change_pct} format={pct} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** 不打扰的连接状态指示（断线时保留最后已知价格，不弹窗报错） */
function LiveStatus() {
  const live = usePriceStreamStatus()
  const paused = usePriceStreamPaused()
  if (paused) {
    return (
      <span className="live-status live-paused" style={{ marginLeft: 10 }}>
        <span className="live-dot" />
        {t('common.paused')}
      </span>
    )
  }
  return (
    <span className={`live-status ${live ? 'live-on' : 'live-off'}`} style={{ marginLeft: 10 }}>
      <span className="live-dot" />
      {live ? t('common.live') : t('common.liveConnecting')}
    </span>
  )
}

export default function Markets() {
  const { worldId } = useCurrentWorld()
  const navigate = useNavigate()
  const [data, setData] = useState<Breadth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await axios.get('/api/v1/analytics/breadth', { params: { world_id: worldId } })
      if (res.data && res.data.error) throw new Error(res.data.error)
      setData(res.data)
      setError(null)
    } catch (err) {
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
  }, [worldId])

  useEffect(() => {
    load()
    // 模拟推进行程后数据会变，轮询让页面跟随刷新
    const timer = setInterval(load, 30000)
    return () => clearInterval(timer)
  }, [load])

  const header = (
    <div className="page-header">
      <h2>{t('markets.title')}</h2>
      <p className="subtitle">{t('markets.subtitle')}</p>
      <LiveStatus />
    </div>
  )

  if (loading) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="error" style={{ padding: 40 }}>{error || t('common.dataError')}</div>
        </div>
      </div>
    )
  }

  // 核心指数优先，不足 4 个时用其余指数补齐
  const featured: Quote[] = []
  for (const tk of FEATURED_INDEX) {
    const hit = data.indices.find((i) => i.ticker === tk)
    if (hit) featured.push(hit)
  }
  for (const idx of data.indices) {
    if (featured.length >= 4) break
    if (!featured.some((f) => f.ticker === idx.ticker)) featured.push(idx)
  }

  const maxBucket = Math.max(1, ...Object.values(data.distribution))

  return (
    <div>
      {header}

      <div className="grid-4">
        {featured.map((idx) => (
          <div className="card" key={idx.ticker}>
            <div className="card-header">
              <span className="card-title">{idx.name}</span>
              <span className={`tag ${idx.change_pct >= 0 ? 'tag-green' : 'tag-red'}`}>
                <LiveChange ticker={idx.ticker} fallback={idx.change_pct} format={pct} />
              </span>
            </div>
            <div className="stat-value">
              <LivePrice ticker={idx.ticker} fallback={idx.price} format={(v) => v.toLocaleString()} />
            </div>
            <div className={`stat-change ${dirClass(idx.change_pct)}`}>{idx.ticker}</div>
          </div>
        ))}
      </div>

      <div className="grid-4">
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.advancing')}</span></div>
          <div className="stat-value positive">{data.advancing}</div>
          <div className="stat-change">{data.advancers_pct}% {t('markets.ofTotal')}</div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.declining')}</span></div>
          <div className="stat-value negative">{data.declining}</div>
          <div className="stat-change">{data.decliners_pct}% {t('markets.ofTotal')}</div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.adLine')}</span></div>
          <div className={`stat-value ${dirClass(data.advance_decline_line)}`}>{data.advance_decline_line}</div>
          <div className="stat-change">
            {t('markets.adRatio')}: {data.advance_decline_ratio ?? '—'}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.avgChange')}</span></div>
          <div className={`stat-value ${dirClass(data.avg_change_pct)}`}>{pct(data.avg_change_pct)}</div>
          <div className="stat-change">
            {t('markets.newHighLow')}: {data.new_highs}/{data.new_lows}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('markets.distribution')}</span>
          <span className="tag tag-gray">{data.total_tracked} {t('markets.instruments')}</span>
        </div>
        <div style={{ padding: 16 }}>
          {DIST_BUCKETS.map(([key, label]) => {
            const v = data.distribution[key] || 0
            const color =
              key.startsWith('below') || key.startsWith('-5_') || key.startsWith('-2_')
                ? 'var(--accent-red)'
                : key === '-0.5_to_0.5'
                ? 'var(--text-secondary)'
                : 'var(--accent-green)'
            return (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <span style={{ width: 90, fontSize: 12, color: 'var(--text-secondary)' }}>{label}</span>
                <div style={{ flex: 1, background: 'var(--bg-tertiary)', borderRadius: 4, height: 14 }}>
                  <div style={{ width: `${(v / maxBucket) * 100}%`, background: color, height: 14, borderRadius: 4 }} />
                </div>
                <span style={{ width: 40, textAlign: 'right', fontSize: 12 }}>{v}</span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('markets.sectors')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('markets.sector')}</th>
              <th>{t('markets.count')}</th>
              <th>{t('markets.advancing')}</th>
              <th>{t('markets.declining')}</th>
              <th>{t('markets.avgChange')}</th>
            </tr>
          </thead>
          <tbody>
            {data.sectors.map((s) => (
              <tr key={s.sector}>
                <td>{s.sector}</td>
                <td>{s.count}</td>
                <td className="positive">{s.advancing}</td>
                <td className="negative">{s.declining}</td>
                <td className={dirClass(s.avg_change_pct)}>{pct(s.avg_change_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid-3">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('markets.gainers')}</span>
            <span className="tag tag-red">TOP {data.gainers.length}</span>
          </div>
          <QuoteTable rows={data.gainers} valueLabel={t('markets.price')} />
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('markets.losers')}</span>
            <span className="tag tag-green">TOP {data.losers.length}</span>
          </div>
          <QuoteTable rows={data.losers} valueLabel={t('markets.price')} />
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('markets.mostActive')}</span>
            <span className="tag tag-blue">VOL</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('markets.code')}</th>
                <th>{t('markets.volume')}</th>
                <th>{t('markets.change')}</th>
              </tr>
            </thead>
            <tbody>
              {data.most_active.map((r) => (
                <tr
                  key={r.ticker}
                  style={rowClickStyle}
                  onClick={() => navigate(`/asset/${encodeURIComponent(r.ticker)}`)}
                  title={t('assetDetail.viewDetail')}
                >
                  <td>{r.ticker}</td>
                  <td>{r.volume.toLocaleString()}</td>
                  <td>
                    <LiveChange ticker={r.ticker} fallback={r.change_pct} format={pct} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('markets.globalIndices')}</span>
          <span className="tag tag-gray">{data.indices.length}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('markets.code')}</th>
              <th>{t('markets.name')}</th>
              <th>{t('markets.price')}</th>
              <th>{t('markets.change')}</th>
            </tr>
          </thead>
          <tbody>
            {data.indices.map((idx) => (
              <tr
                key={idx.ticker}
                style={rowClickStyle}
                onClick={() => navigate(`/asset/${encodeURIComponent(idx.ticker)}`)}
                title={t('assetDetail.viewDetail')}
              >
                <td>{idx.ticker}</td>
                <td>{idx.name}</td>
                <td>
                  <LivePrice ticker={idx.ticker} fallback={idx.price} format={(v) => v.toLocaleString()} />
                </td>
                <td>
                  <LiveChange ticker={idx.ticker} fallback={idx.change_pct} format={pct} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
