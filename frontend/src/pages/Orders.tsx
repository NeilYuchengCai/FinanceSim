import { useState, useEffect } from 'react'
import axios from 'axios'

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

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Form state
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
      setError('Failed to load order data')
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
      setError('Failed to submit order')
    } finally {
      setSubmitting(false)
    }
  }

  const cancelOrder = async (orderId: string) => {
    try {
      await axios.put(`/api/trading/orders/${orderId}/cancel?world_id=1`)
      await fetchOrders()
    } catch (err) {
      setError('Failed to cancel order')
    }
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>Orders</h2>
          <p className="subtitle">Order management</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading...</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>Orders</h2>
        <p className="subtitle">Order management</p>
      </div>
      
      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">New Order</span>
          </div>
          <form onSubmit={handleSubmitOrder}>
            <div style={{ marginBottom: 12 }}>
              <label>Ticker</label>
              <input 
                type="text" 
                className="input-field" 
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL"
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Side</label>
              <select className="input-field" value={side} onChange={(e) => setSide(e.target.value)}>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Type</label>
              <select className="input-field" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
                <option value="STOP">STOP</option>
                <option value="STOP_LIMIT">STOP_LIMIT</option>
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Quantity</label>
              <input 
                type="number" 
                className="input-field" 
                value={quantity}
                onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                min={1}
              />
            </div>
            {(type === 'LIMIT' || type === 'STOP' || type === 'STOP_LIMIT') && (
              <div style={{ marginBottom: 12 }}>
                <label>{type === 'STOP' || type === 'STOP_LIMIT' ? 'Stop Price' : 'Limit Price'}</label>
                <input 
                  type="number" 
                  className="input-field" 
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="100.00"
                  step="0.01"
                />
              </div>
            )}
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%' }}
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Submit Order'}
            </button>
          </form>
        </div>
        
        <div className="card">
          <div className="card-header">
            <span className="card-title">Recent Trades</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.length > 0 ? (
                trades.slice(0, 10).map((trade) => (
                  <tr key={trade.id}>
                    <td><strong>{trade.ticker}</strong></td>
                    <td className={trade.side === 'BUY' ? 'positive' : 'negative'}>{trade.side}</td>
                    <td>{trade.quantity}</td>
                    <td>${trade.price.toFixed(2)}</td>
                    <td>{new Date(trade.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={5} className="loading">No trades yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Open Orders</span>
          <button className="btn btn-sm" onClick={fetchOrders}>Refresh</button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Ticker</th>
              <th>Side</th>
              <th>Type</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.length > 0 ? (
              orders.map((order) => (
                <tr key={order.id}>
                  <td style={{fontSize: 11}}>{order.id.slice(0, 8)}...</td>
                  <td><strong>{order.ticker}</strong></td>
                  <td className={order.side === 'BUY' ? 'positive' : 'negative'}>{order.side}</td>
                  <td>{order.type}</td>
                  <td>{order.quantity}</td>
                  <td>${order.price?.toFixed(2) || '--'}</td>
                  <td>
                    <span className={`tag ${
                      order.status === 'FILLED' ? 'tag-green' :
                      order.status === 'CANCELLED' ? 'tag-gray' : 'tag-blue'
                    }`}>
                      {order.status}
                    </span>
                  </td>
                  <td>
                    {order.status === 'PENDING' && (
                      <button 
                        className="btn btn-sm btn-danger"
                        onClick={() => cancelOrder(order.id)}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={8} className="loading">No open orders</td></tr>
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
