import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import { usePriceQuote } from '../hooks/usePriceStream'
import OHLCChart from '../components/charts/OHLCChart'
import ErrorBoundary from '../components/ErrorBoundary'
import OrderForm from '../components/OrderForm'

/**
 * 资产详情页（P1-17，"可交易"定位的关键缺口）
 *
 * 路由：/asset/:ticker（ticker 经 encodeURIComponent，含 . / 的代码如 EUR/USD、BRK.B 均可）
 *
 * 数据契约（已与后端核对）：
 * - GET /api/v1/assets/{ticker}?world_id={worldId}            -> AssetResponse
 * - GET /api/v1/assets/price-history?ticker=&world_id=&limit= -> [{time,open,high,low,close,volume}]
 * - GET /api/v1/trading/orderbook/{ticker}?world_id={worldId} -> {bids:[{price,quantity}],asks:[...]}
 * - 下单复用共享组件 OrderForm（POST /api/v1/trading/orders）
 */

interface AssetInfo {
  ticker: string
  type: string
  name?: string | null
  exchange?: string | null
  sector?: string | null
  industry?: string | null
  currency: string
  market_cap?: number | null
  beta?: number | null
  volatility?: number | null
  current_price?: number | null
}

interface PriceBar {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

interface OrderBookLevel {
  price: number
  quantity: number
}

interface OrderBook {
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
}

const HISTORY_LIMIT = 120

function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  if (Math.abs(value) >= 1e12) return `${(value / 1e12).toFixed(2)}T`
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)}亿`
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(2)}万`
  return value.toLocaleString()
}

export default function AssetDetail() {
  const { ticker: encodedTicker } = useParams<{ ticker: string }>()
  const ticker = decodeURIComponent(encodedTicker ?? '')
  const { worldId } = useCurrentWorld()
  const quote = usePriceQuote(ticker)

  const [asset, setAsset] = useState<AssetInfo | null>(null)
  const [bars, setBars] = useState<PriceBar[]>([])
  const [orderbook, setOrderbook] = useState<OrderBook | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!ticker) return
    setLoading(true)
    setError(null)
    try {
      const [assetRes, barsRes] = await Promise.all([
        axios.get<AssetInfo>(`/api/v1/assets/${encodeURIComponent(ticker)}`, {
          params: { world_id: worldId },
        }),
        axios.get<PriceBar[]>('/api/v1/assets/price-history', {
          params: { ticker, world_id: worldId, limit: HISTORY_LIMIT },
        }),
      ])
      setAsset(assetRes.data)
      setBars(Array.isArray(barsRes.data) ? barsRes.data : [])
    } catch {
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
  }, [ticker, worldId])

  const loadOrderbook = useCallback(async () => {
    if (!ticker) return
    try {
      const res = await axios.get<OrderBook>(
        `/api/v1/trading/orderbook/${encodeURIComponent(ticker)}`,
        { params: { world_id: worldId } },
      )
      setOrderbook(res.data)
    } catch {
      // 订单簿拿不到不打断整页（新标的无挂单时可能为空）
      setOrderbook(null)
    }
  }, [ticker, worldId])

  useEffect(() => {
    load()
    loadOrderbook()
  }, [load, loadOrderbook])

  const displayPrice = quote?.price ?? asset?.current_price ?? null
  const changePct = quote?.changePct ?? null

  const header = (
    <div className="page-header">
      <h2>
        {asset?.name ?? ticker}{' '}
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.7em' }}>{ticker}</span>
      </h2>
      <p className="subtitle">
        {displayPrice !== null ? (
          <span
            className={changePct !== null && changePct >= 0 ? 'cn-up' : changePct !== null ? 'cn-down' : ''}
            style={{ fontSize: '1.4em', fontWeight: 600 }}
          >
            {displayPrice.toLocaleString()}
            {changePct !== null ? ` (${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%)` : ''}
          </span>
        ) : (
          t('common.noData')
        )}
      </p>
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

  if (error || !asset) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="error" style={{ padding: 40 }}>{error ?? t('common.dataError')}</div>
          <button className="btn" style={{ marginTop: 12 }} onClick={load}>
            {t('common.retry')}
          </button>
        </div>
      </div>
    )
  }

  const infoItems: { label: string; value: string }[] = [
    { label: t('equities.ticker'), value: asset.ticker },
    { label: t('assetDetail.type'), value: asset.type },
    { label: t('equities.exchange'), value: asset.exchange ?? '—' },
    { label: t('equities.sector'), value: asset.sector ?? '—' },
    { label: t('assetDetail.industry'), value: asset.industry ?? '—' },
    { label: t('assetDetail.currency'), value: asset.currency },
    { label: t('equities.marketCap'), value: formatCompact(asset.market_cap) },
    { label: t('analytics.beta'), value: asset.beta != null ? asset.beta.toFixed(2) : '—' },
    { label: t('analytics.volatility'), value: asset.volatility != null ? `${(asset.volatility * 100).toFixed(2)}%` : '—' },
  ]

  const renderLevels = (levels: OrderBookLevel[] | undefined, side: 'bid' | 'ask') => {
    if (!levels || levels.length === 0) {
      return (
        <tr>
          <td colSpan={2} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 12 }}>
            {t('common.noData')}
          </td>
        </tr>
      )
    }
    return (
      <>
        {levels.map((lv, i) => (
          <tr key={`${side}-${i}`}>
            <td className={side === 'bid' ? 'cn-up' : 'cn-down'}>{lv.price.toLocaleString()}</td>
            <td>{lv.quantity}</td>
          </tr>
        ))}
      </>
    )
  }

  return (
    <div>
      {header}

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('assetDetail.basicInfo')}</span>
          </div>
          <table className="data-table">
            <tbody>
              {infoItems.map((item) => (
                <tr key={item.label}>
                  <td style={{ color: 'var(--text-secondary)', width: 120 }}>{item.label}</td>
                  <td>{item.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('assetDetail.orderbook')}</span>
            <button className="btn btn-sm" onClick={loadOrderbook}>{t('common.refresh')}</button>
          </div>
          <div className="grid-2">
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                {t('orders.buy')} ({t('assetDetail.bids')})
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('equities.price')}</th>
                    <th>{t('orders.quantity')}</th>
                  </tr>
                </thead>
                <tbody>{renderLevels(orderbook?.bids, 'bid')}</tbody>
              </table>
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                {t('orders.sell')} ({t('assetDetail.asks')})
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('equities.price')}</th>
                    <th>{t('orders.quantity')}</th>
                  </tr>
                </thead>
                <tbody>{renderLevels(orderbook?.asks, 'ask')}</tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('timeline.priceChart')}</span>
          <button className="btn btn-sm" onClick={load}>{t('common.refresh')}</button>
        </div>
        {bars.length > 0 ? (
          <ErrorBoundary label="priceChart">
            <OHLCChart data={bars} height={400} symbol={ticker} />
          </ErrorBoundary>
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            {t('assetDetail.noHistory')}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('assetDetail.trade')}</span>
        </div>
        <OrderForm
          worldId={worldId}
          fixedTicker={ticker}
          onSubmitted={() => {
            loadOrderbook()
          }}
        />
      </div>
    </div>
  )
}
