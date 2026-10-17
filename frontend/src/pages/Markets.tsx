import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { LivePrice, LiveChange } from '../components/LiveQuote'
import { usePriceStreamStatus } from '../hooks/usePriceStream'
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

function QuoteTable({ rows, valueLabel }: { rows: Quote[]; valueLabel: string }) {
  if (!rows.length) return <div className="loading">{t('common.noData', '暂无数据')}</div>
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>{t('markets.code', '代码')}</th>
          <th>{valueLabel}</th>
          <th>{t('markets.change', '涨跌幅')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.ticker}>
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
  return (
    <span className={`live-status ${live ? 'live-on' : 'live-off'}`} style={{ marginLeft: 10 }}>
      <span className="live-dot" />
      {live ? t('common.live', '实时行情') : t('common.liveConnecting', '连接中…')}
    </span>
  )
}

export default function Markets() {
  const { worldId } = useCurrentWorld()
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
      setError(t('common.dataError', '数据加载失败'))
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
      <h2>{t('markets.title', '市场概览')}</h2>
      <p className="subtitle">{t('markets.subtitle', '指数行情、市场广度与板块表现')}</p>
      <LiveStatus />
    </div>
  )

  if (loading) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="loading" style={{ padding: 40 }}>{t('common.loading', '加载中...')}</div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="error" style={{ padding: 40 }}>{error || t('common.dataError', '数据加载失败')}</div>
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
          <div className="card-header"><span className="card-title">{t('markets.advancing', '上涨家数')}</span></div>
          <div className="stat-value positive">{data.advancing}</div>
          <div className="stat-change">{data.advancers_pct}% {t('markets.ofTotal', '占比')}</div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.declining', '下跌家数')}</span></div>
          <div className="stat-value negative">{data.declining}</div>
          <div className="stat-change">{data.decliners_pct}% {t('markets.ofTotal', '占比')}</div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.adLine', '腾落线 A-D')}</span></div>
          <div className={`stat-value ${dirClass(data.advance_decline_line)}`}>{data.advance_decline_line}</div>
          <div className="stat-change">
            {t('markets.adRatio', '涨跌比')}: {data.advance_decline_ratio ?? '—'}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">{t('markets.avgChange', '平均涨跌')}</span></div>
          <div className={`stat-value ${dirClass(data.avg_change_pct)}`}>{pct(data.avg_change_pct)}</div>
          <div className="stat-change">
            {t('markets.newHighLow', '新高/新低')}: {data.new_highs}/{data.new_lows}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('markets.distribution', '涨跌幅分布')}</span>
          <span className="tag tag-gray">{data.total_tracked} {t('markets.instruments', '只标的')}</span>
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
          <span className="card-title">{t('markets.sectors', '板块表现')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('markets.sector', '板块')}</th>
              <th>{t('markets.count', '数量')}</th>
              <th>{t('markets.advancing', '上涨')}</th>
              <th>{t('markets.declining', '下跌')}</th>
              <th>{t('markets.avgChange', '平均涨跌')}</th>
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
            <span className="card-title">{t('markets.gainers', '涨幅榜')}</span>
            <span className="tag tag-red">TOP {data.gainers.length}</span>
          </div>
          <QuoteTable rows={data.gainers} valueLabel={t('markets.price', '现价')} />
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('markets.losers', '跌幅榜')}</span>
            <span className="tag tag-green">TOP {data.losers.length}</span>
          </div>
          <QuoteTable rows={data.losers} valueLabel={t('markets.price', '现价')} />
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('markets.mostActive', '活跃榜')}</span>
            <span className="tag tag-blue">VOL</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('markets.code', '代码')}</th>
                <th>{t('markets.volume', '成交量')}</th>
                <th>{t('markets.change', '涨跌幅')}</th>
              </tr>
            </thead>
            <tbody>
              {data.most_active.map((r) => (
                <tr key={r.ticker}>
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
          <span className="card-title">{t('markets.globalIndices', '全球主要指数')}</span>
          <span className="tag tag-gray">{data.indices.length}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('markets.code', '代码')}</th>
              <th>{t('markets.name', '名称')}</th>
              <th>{t('markets.price', '点位')}</th>
              <th>{t('markets.change', '涨跌幅')}</th>
            </tr>
          </thead>
          <tbody>
            {data.indices.map((idx) => (
              <tr key={idx.ticker}>
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
