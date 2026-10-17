import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { t } from '../i18n'
import { usePriceStream, usePriceStreamStatus, usePriceStreamPaused, type PriceQuote } from '../hooks/usePriceStream'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import { LivePrice, LiveChange } from '../components/LiveQuote'

interface Asset {
  id: number
  ticker: string
  type: string
  name: string
  exchange: string
  sector: string
  industry: string
  currency: string
  market_cap: number
  beta: number
  volatility: number
  fundamentals: Record<string, any>
  // 仅当请求带 with_change=1 时后端才填充
  current_price?: number | null
  prev_close?: number | null
  change_pct?: number | null
  last_volume?: number | null
}

// ---------------------------------------------------------------- 格式化
const formatChange = (chg: number | null | undefined) => {
  if (chg === null || chg === undefined || Number.isNaN(chg)) return '--'
  return `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`
}

const formatVolume = (v: number | null | undefined) => {
  if (v === null || v === undefined) return '--'
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`
  return String(Math.round(v))
}

const formatMarketCap = (mc: number | null | undefined) => {
  if (mc === null || mc === undefined || Number.isNaN(mc)) return '--'
  return mc >= 1000 ? `${(mc / 1000).toFixed(1)}T` : `${mc.toFixed(0)}B`
}

// ---------------------------------------------------------------- 连接状态
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

// ---------------------------------------------------------------- 榜单
function TopMovers({ assets }: { assets: Asset[] }) {
  // 榜单只有 3 张卡片，用整表视角订阅不会造成表格重渲染
  const { prices } = usePriceStream()

  const rows = assets.map((a) => {
    const q: PriceQuote | undefined = prices.get(a.ticker)
    return {
      asset: a,
      change: q ? q.changePct : a.change_pct ?? null,
      volume: a.last_volume ?? null,
    }
  })

  const withChange = rows.filter((r) => r.change !== null && r.change !== undefined)
  const topGainer = withChange.length
    ? withChange.reduce((a, b) => ((b.change ?? 0) > (a.change ?? 0) ? b : a))
    : null
  const topLoser = withChange.length
    ? withChange.reduce((a, b) => ((b.change ?? 0) < (a.change ?? 0) ? b : a))
    : null
  const mostActive = rows.some((r) => r.volume)
    ? rows.reduce((a, b) => ((b.volume ?? 0) > (a.volume ?? 0) ? b : a))
    : null

  return (
    <div className="grid-3" style={{ marginTop: 20 }}>
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('equities.topGainers')}</span>
        </div>
        <div style={{ padding: 20, textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', color: 'var(--accent-green)' }}>
            {topGainer ? formatChange(topGainer.change) : '--'}
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
            {topGainer ? `${topGainer.asset.name} (${topGainer.asset.ticker})` : t('equities.noData')}
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('equities.topLosers')}</span>
        </div>
        <div style={{ padding: 20, textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', color: 'var(--accent-red)' }}>
            {topLoser ? formatChange(topLoser.change) : '--'}
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
            {topLoser ? `${topLoser.asset.name} (${topLoser.asset.ticker})` : t('equities.noData')}
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('equities.mostActive')}</span>
        </div>
        <div style={{ padding: 20, textAlign: 'center' }}>
          <div style={{ fontSize: '2rem' }}>{mostActive ? formatVolume(mostActive.volume) : '--'}</div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
            {mostActive ? `${mostActive.asset.name} (${mostActive.asset.ticker})` : t('equities.noData')}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- 页面
export default function Equities() {
  const { worldId } = useCurrentWorld()
  const navigate = useNavigate()
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    const fetchAssets = async () => {
      try {
        // with_change=1 让后端附带真实涨跌幅与最新成交量作为断线时的兜底数据
        const res = await axios.get(`/api/v1/assets?world_id=${worldId}&type=EQUITY&limit=500&with_change=1`)
        setAssets(res.data)
      } catch (err) {
        setError(t('common.dataError'))
      } finally {
        setLoading(false)
      }
    }
    fetchAssets()
  }, [worldId])

  const filtered = filter === 'ALL' ? assets : assets.filter((a) => a.sector === filter)
  const sectors = [...new Set(assets.map((a) => a.sector))]

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('equities.title')}</h2>
          <p className="subtitle">{t('equities.subtitle')}</p>
        </div>
        <div className="card">
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('equities.title')}</h2>
          <p className="subtitle">{t('equities.subtitle')}</p>
        </div>
        <div className="card">
          <div className="error" style={{ padding: 40 }}>{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('equities.title')}</h2>
        <p className="subtitle">{t('equities.subtitle')} · {assets.length} stocks</p>
        <LiveStatus />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('equities.filter')}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            onClick={() => setFilter('ALL')}
            style={{
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid var(--border-color)',
              background: filter === 'ALL' ? 'var(--accent-color)' : 'var(--bg-secondary)',
              color: filter === 'ALL' ? 'white' : 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {t('equities.all')}
          </button>
          {sectors.map((sector) => (
            <button
              key={sector}
              onClick={() => setFilter(sector)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: '1px solid var(--border-color)',
                background: filter === sector ? 'var(--accent-color)' : 'var(--bg-secondary)',
                color: filter === sector ? 'white' : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {sector}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('equities.marketSummary')}</span>
          <span className="tag tag-blue">SIMULATION</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('equities.change')}</th>
              <th>{t('equities.volume')}</th>
              <th>{t('equities.marketCap')}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((asset) => (
              // key 稳定用 id，排序不随实时价格变化，滚动位置不会跳动
              <tr
                key={asset.id}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/asset/${encodeURIComponent(asset.ticker)}`)}
                title={t('assetDetail.viewDetail')}
              >
                <td>{asset.ticker}</td>
                <td>{asset.name}</td>
                <td>
                  <LivePrice ticker={asset.ticker} fallback={asset.current_price ?? null} />
                </td>
                <td>
                  <LiveChange ticker={asset.ticker} fallback={asset.change_pct ?? null} />
                </td>
                <td>{formatVolume(asset.last_volume)}</td>
                <td>{formatMarketCap(asset.market_cap)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <TopMovers assets={filtered} />
    </div>
  )
}
