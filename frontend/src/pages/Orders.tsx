import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import { useToast } from '../components/Toast'
import OrderForm from '../components/OrderForm'

/**
 * 订单页（Wave 2 修复）
 *
 * 契约（已与后端核对，2026-10 联调）：
 * - GET  /api/v1/trading/orders?world_id=   -> 仅未成交订单（PENDING/PARTIAL，排除 BOT 单），
 *   字段：id/ticker/side/type/status/quantity/filled_quantity/price(nullable)/created_by/created_at
 * - GET  /api/v1/trading/trades?world_id=&limit= -> DB+内存合并成交，
 *   字段：id/ticker/price/quantity/timestamp/order_id_buy/order_id_sell/buyer_order_id/
 *         seller_order_id/world_id/world_day（暂无 direction/side 字段）
 * - POST /api/v1/trading/orders?world_id=   -> 提交订单
 * - PUT  /api/v1/trading/orders/{id}/cancel?world_id=
 *
 * 成交方向妥协（后端 direction 字段在途）：若响应带 direction/side 则直接用；
 * 否则按 order_id_buy/order_id_sell 与本页提交成功的订单 id 集合推断，
 * 推断不出（如机器人成交）显示 '—'，不猜测。
 */

interface Order {
  id: string
  ticker: string
  side: string
  type: string
  status: string
  quantity: number
  filled_quantity?: number
  price: number | null
  created_at: string
}

interface Trade {
  id: string
  ticker: string
  price: number
  quantity: number
  timestamp: string | null
  order_id_buy?: string | null
  order_id_sell?: string | null
  buyer_order_id?: string | null
  seller_order_id?: string | null
  world_day?: number | null
  /** 后端后续版本可能补充的方向字段，存在即用 */
  direction?: string | null
  side?: string | null
}

const SIDE_LABELS: Record<string, string> = { BUY: '买入', SELL: '卖出' }
const TYPE_LABELS: Record<string, string> = { MARKET: '市价', LIMIT: '限价', STOP: '止损', STOP_LIMIT: '止损限价' }
const STATUS_LABELS: Record<string, string> = { FILLED: '已成交', PENDING: '待成交', PARTIAL: '部分成交', CANCELLED: '已取消' }

/** 无效/缺失时间统一显示 '—'（避免 new Date(undefined) 渲染出 Invalid Date） */
function formatTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN')
}

function normalizeSide(value: string | null | undefined): 'BUY' | 'SELL' | null {
  if (!value) return null
  const v = value.toUpperCase()
  if (v === 'BUY' || v === 'B' || v === 'BID') return 'BUY'
  if (v === 'SELL' || v === 'S' || v === 'ASK') return 'SELL'
  return null
}

export default function Orders() {
  const { worldId } = useCurrentWorld()
  const toast = useToast()
  const [orders, setOrders] = useState<Order[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [assets, setAssets] = useState<{ ticker: string; name?: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // 本页提交成功的订单 id：用于在 direction 字段缺失时推断成交方向
  const [submittedOrderIds, setSubmittedOrderIds] = useState<Set<string>>(new Set());

  const fetchOrders = useCallback(async () => {
    try {
      const [ordersRes, tradesRes] = await Promise.all([
        axios.get(`/api/v1/trading/orders?world_id=${worldId}`),
        axios.get(`/api/v1/trading/trades?world_id=${worldId}&limit=50`),
      ])
      setOrders(Array.isArray(ordersRes.data) ? ordersRes.data : [])
      setTrades(Array.isArray(tradesRes.data) ? tradesRes.data : [])
    } catch {
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
  }, [worldId]);

  // 资产列表：仅用于下单框的 ticker 联想与存在性校验
  useEffect(() => {
    const loadAssets = async () => {
      try {
        const res = await axios.get('/api/v1/assets', {
          params: { world_id: worldId, limit: 500 },
        })
        const list: unknown[] = Array.isArray(res.data) ? res.data : []
        setAssets(
          list
            .map((a) => {
              const row = a as { ticker?: unknown; name?: unknown }
              return {
                ticker: typeof row.ticker === 'string' ? row.ticker : '',
                name: typeof row.name === 'string' ? row.name : undefined,
              }
            })
            .filter((a) => a.ticker.length > 0),
        )
      } catch {
        // 联想列表拿不到不拦截下单，仅失去补全能力
        setAssets([])
      }
    }
    loadAssets()
  }, [worldId])

  useEffect(() => {
    fetchOrders()
  }, [fetchOrders])

  const handleSubmitted = (orderId?: string) => {
    if (orderId) {
      setSubmittedOrderIds((prev) => {
        const next = new Set(prev)
        next.add(orderId)
        return next
      })
    }
    fetchOrders()
  }

  const cancelOrder = async (orderId: string) => {
    try {
      await axios.put(`/api/v1/trading/orders/${orderId}/cancel?world_id=${worldId}`)
      await fetchOrders()
      toast.success(t('toast.orderCancelled'))
    } catch {
      toast.error(t('toast.orderCancelFailed'))
    }
  }

  const inferDirection = (trade: Trade): 'BUY' | 'SELL' | null => {
    // 1) 后端若已提供 direction/side 字段，直接使用
    const explicit = normalizeSide(trade.direction) ?? normalizeSide(trade.side)
    if (explicit) return explicit
    // 2) 妥协推断：与本页提交过的订单 id 匹配（见文件头注释）
    const buyId = trade.order_id_buy ?? trade.buyer_order_id
    const sellId = trade.order_id_sell ?? trade.seller_order_id
    if (buyId && submittedOrderIds.has(buyId)) return 'BUY'
    if (sellId && submittedOrderIds.has(sellId)) return 'SELL'
    return null
  }

  const header = (
    <div className="page-header">
      <h2>{t('orders.title')}</h2>
      <p className="subtitle">{t('orders.subtitle')}</p>
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

  return (
    <div>
      {header}

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('orders.newOrder')}</span>
          </div>
          <OrderForm worldId={worldId} assets={assets} onSubmitted={handleSubmitted} />
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('orders.recentTrades')}</span>
            <button className="btn btn-sm" onClick={fetchOrders}>{t('common.refresh')}</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('equities.ticker')}</th>
                <th>{t('orders.direction')}</th>
                <th>{t('orders.quantity')}</th>
                <th>{t('orders.price')}</th>
                <th>{t('orders.time')}</th>
              </tr>
            </thead>
            <tbody>
              {trades.length > 0 ? (
                trades.slice(0, 20).map((trade) => {
                  const direction = inferDirection(trade)
                  return (
                    <tr key={trade.id}>
                      <td><strong>{trade.ticker}</strong></td>
                      <td className={direction === 'BUY' ? 'cn-up' : direction === 'SELL' ? 'cn-down' : undefined}>
                        {direction ? (direction === 'BUY' ? t('orders.buy') : t('orders.sell')) : '—'}
                      </td>
                      <td>{trade.quantity}</td>
                      <td>{trade.price != null ? `$${trade.price.toFixed(2)}` : '—'}</td>
                      <td>{formatTime(trade.timestamp)}</td>
                    </tr>
                  )
                })
              ) : (
                <tr><td colSpan={5} className="loading">{t('orders.noTrades')}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('orders.openOrders')}</span>
          <button className="btn btn-sm" onClick={fetchOrders}>{t('common.refresh')}</button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>{t('equities.ticker')}</th>
              <th>{t('orders.side')}</th>
              <th>{t('orders.type')}</th>
              <th>{t('orders.quantity')}</th>
              <th>{t('orders.price')}</th>
              <th>{t('orders.status')}</th>
              <th>{t('orders.createdAt')}</th>
              <th>{t('orders.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {orders.length > 0 ? (
              orders.map((order) => (
                <tr key={order.id}>
                  <td style={{ fontSize: 11 }}>{order.id.slice(0, 8)}...</td>
                  <td><strong>{order.ticker}</strong></td>
                  <td className={order.side === 'BUY' ? 'cn-up' : 'cn-down'}>{SIDE_LABELS[order.side] || order.side}</td>
                  <td>{TYPE_LABELS[order.type] || order.type}</td>
                  <td>{order.quantity}</td>
                  <td>{order.price != null ? `$${order.price.toFixed(2)}` : '—'}</td>
                  <td>
                    <span className={`tag ${order.status === 'FILLED' ? 'tag-green' : order.status === 'CANCELLED' ? 'tag-gray' : 'tag-blue'}`}>
                      {STATUS_LABELS[order.status] || order.status}
                    </span>
                  </td>
                  <td>{formatTime(order.created_at)}</td>
                  <td>
                    {order.status === 'PENDING' && (
                      <button className="btn btn-sm btn-danger" onClick={() => cancelOrder(order.id)}>{t('orders.cancel')}</button>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={9} className="loading">{t('orders.noOrders')}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--accent-red)' }}>
          <div className="error" style={{ padding: 16 }}>{error}</div>
        </div>
      )}
    </div>
  )
}
