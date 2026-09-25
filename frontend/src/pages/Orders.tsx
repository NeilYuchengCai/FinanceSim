import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'

interface Order {
  id: string
  ticker: string
  side: string
  type: string
  quantity: number
  price: number
  status: string
  created_at: string
}

interface Trade {
  id: string
  ticker: string
  side: string
  quantity: number
  price: number
  timestamp: string
}

const SIDE_LABELS: Record<string, string> = { BUY: '买入', SELL: '卖出' }
const TYPE_LABELS: Record<string, string> = { MARKET: '市价', LIMIT: '限价', STOP: '止损', STOP_LIMIT: '止损限价' }
const STATUS_LABELS: Record<string, string> = { FILLED: '已成交', PENDING: '待成交', CANCELLED: '已取消' }

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [ticker, setTicker] = useState('AAPL')
  const [side, setSide] = useState('BUY')
  const [type, setType] = useState('MARKET')
  const [quantity, setQuantity] = useState(100)
  const [price, setPrice] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchOrders = async () => {
    try {
      const [ordersRes, tradesRes] = await Promise.all([
        axios.get('/api/trading/orders?world_id=1'),
        axios.get('/api/trading/trades?world_id=1&limit=50')
      ])
      setOrders(ordersRes.data || [])
      setTrades(tradesRes.data || [])
    } catch (err) {
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await axios.post(`/api/trading/orders?world_id=1`, {
        asset_ticker: ticker,
        side: side,
        type: type,
        quantity: quantity,
        price: type === 'LIMIT' || type === 'STOP_LIMIT' ? parseFloat(price) : undefined,
        stop_price: type === 'STOP' || type === 'STOP_LIMIT' ? parseFloat(price) : undefined
      })
      await fetchOrders()
    } catch (err) {
      setError(t('common.error'))
    } finally {
      setSubmitting(false)
    }
  }

  const cancelOrder = async (orderId: string) => {
    try {
      await axios.put(`/api/trading/orders/${orderId}/cancel?world_id=1`)
      await fetchOrders()
    } catch (err) {
      setError(t('common.error'))
    }
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('orders.title')}</h2>
          <p className="subtitle">{t('orders.subtitle', '查看和管理交易订单')}</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>{t('common.loading')}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('orders.title')}</h2>
        <p className="subtitle">{t('orders.subtitle', '查看和管理交易订单')}</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('orders.newOrder', '新建订单')}</span>
          </div>
          <form onSubmit={handleSubmitOrder}>
            <div style={{ marginBottom: 12 }}>
              <label>{t('equities.ticker')}</label>
              <input type="text" className="input-field" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="AAPL" />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>{t('orders.side', '买卖方向')}</label>
              <select className="input-field" value={side} onChange={(e) => setSide(e.target.value)}>
                <option value="BUY">{t('orders.buy')}</option>
                <option value="SELL">{t('orders.sell')}</option>
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>{t('orders.orderType', '订单类型')}</label>
              <select className="input-field" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="MARKET">{t('orders.market')}</option>
                <option value="LIMIT">{t('orders.limit')}</option>
                <option value="STOP">{t('orders.stop')}</option>
                <option value="STOP_LIMIT">{t('orders.stopLimit', '止损限价')}</option>
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>{t('orders.quantity')}</label>
              <input type="number" className="input-field" value={quantity} onChange={(e) => setQuantity(parseInt(e.target.value) || 0)} min={1} />
            </div>
            {(type === 'LIMIT' || type === 'STOP' || type === 'STOP_LIMIT') && (
              <div style={{ marginBottom: 12 }}>
                <label>{type === 'STOP' || type === 'STOP_LIMIT' ? t('orders.stopPrice', '止损价') : t('orders.limitPrice', '限价')}</label>
                <input type="number" className="input-field" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="100.00" step="0.01" />
              </div>
            )}
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
              {submitting ? t('orders.submitting', '提交中...') : t('orders.submit', '提交订单')}
            </button>
          </form>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('orders.recentTrades', '最近成交')}</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('equities.ticker')}</th>
                <th>{t('orders.side')}</th>
                <th>{t('orders.quantity')}</th>
                <th>{t('orders.price')}</th>
                <th>{t('orders.time', '时间')}</th>
              </tr>
            </thead>
            <tbody>
              {trades.length > 0 ? (
                trades.slice(0, 10).map((trade) => (
                  <tr key={trade.id}>
                    <td><strong>{trade.ticker}</strong></td>
                    <td className={trade.side === 'BUY' ? 'positive' : 'negative'}>{SIDE_LABELS[trade.side] || trade.side}</td>
                    <td>{trade.quantity}</td>
                    <td>${trade.price.toFixed(2)}</td>
                    <td>{new Date(trade.timestamp).toLocaleTimeString('zh-CN')}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={5} className="loading">{t('orders.noTrades', '暂无成交记录')}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('orders.openOrders', '挂单')}</span>
          <button className="btn btn-sm" onClick={fetchOrders}>{t('common.refresh')}</button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>{t('equities.ticker')}</th>
              <th>{t('orders.side')}</th>
              <th>{t('orders.type', '类型')}</th>
              <th>{t('orders.quantity')}</th>
              <th>{t('orders.price')}</th>
              <th>{t('orders.status')}</th>
              <th>{t('orders.actions', '操作')}</th>
            </tr>
          </thead>
          <tbody>
            {orders.length > 0 ? (
              orders.map((order) => (
                <tr key={order.id}>
                  <td style={{fontSize: 11}}>{order.id.slice(0, 8)}...</td>
                  <td><strong>{order.ticker}</strong></td>
                  <td className={order.side === 'BUY' ? 'positive' : 'negative'}>{SIDE_LABELS[order.side] || order.side}</td>
                  <td>{TYPE_LABELS[order.type] || order.type}</td>
                  <td>{order.quantity}</td>
                  <td>${order.price?.toFixed(2) || '--'}</td>
                  <td><span className={`tag ${order.status === 'FILLED' ? 'tag-green' : order.status === 'CANCELLED' ? 'tag-gray' : 'tag-blue'}`}>{STATUS_LABELS[order.status] || order.status}</span></td>
                  <td>
                    {order.status === 'PENDING' && (
                      <button className="btn btn-sm btn-danger" onClick={() => cancelOrder(order.id)}>{t('orders.cancel', '取消')}</button>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={8} className="loading">{t('orders.noOrders', '暂无挂单')}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {error && (
        <div className="card" style={{borderColor: 'var(--color-danger)'}}>
          <div className="error" style={{padding: 16}}>{error}</div>
        </div>
      )}
    </div>
  )
}
