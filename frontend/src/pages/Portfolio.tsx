import { useState, useEffect } from 'react'
import axios from 'axios'

interface Position {
  ticker: string
  quantity: number
  avg_price: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
}

interface Portfolio {
  total_value: number
  cash: number
  invested: number
  return_pct: number
  positions: Position[]
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [portfolioRes, positionsRes] = await Promise.all([
          axios.get('/api/trading/portfolio?world_id=1'),
          axios.get('/api/trading/portfolio/positions?world_id=1')
        ])
        setPortfolio({
          ...portfolioRes.data,
          positions: positionsRes.data || []
        })
      } catch (err) {
        setError('Failed to load portfolio data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>Portfolio</h2>
          <p className="subtitle">Your investment portfolio</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>Portfolio</h2>
          <p className="subtitle">Your investment portfolio</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  if (!portfolio) return null

  const formatCurrency = (v: number) => `$${v.toFixed(2)}`
  const formatPercent = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`

  return (
    <div>
      <div className="page-header">
        <h2>Portfolio</h2>
        <p className="subtitle">Your investment portfolio</p>
      </div>
      
      <div className="grid-4">
        <div className="card">
          <div className="stat-value">{formatCurrency(portfolio.total_value)}</div>
          <div className="stat-change">Total Value</div>
        </div>
        <div className="card">
          <div className="stat-value">{formatCurrency(portfolio.cash)}</div>
          <div className="stat-change">Cash</div>
        </div>
        <div className="card">
          <div className="stat-value">{formatCurrency(portfolio.invested)}</div>
          <div className="stat-change">Invested</div>
        </div>
        <div className="card">
          <div className={`stat-value ${portfolio.return_pct >= 0 ? 'positive' : 'negative'}`}>
            {formatPercent(portfolio.return_pct)}
          </div>
          <div className="stat-change">Return</div>
        </div>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">Positions</span>
          <span className="tag tag-blue">{portfolio.positions.length} holdings</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Quantity</th>
              <th>Avg Price</th>
              <th>Last Price</th>
              <th>Market Value</th>
              <th>P&L</th>
              <th>P&L %</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.positions.length > 0 ? (
              portfolio.positions.map((pos) => (
                <tr key={pos.ticker}>
                  <td><strong>{pos.ticker}</strong></td>
                  <td>{pos.quantity}</td>
                  <td>{formatCurrency(pos.avg_price)}</td>
                  <td>{formatCurrency(pos.current_price)}</td>
                  <td>{formatCurrency(pos.market_value)}</td>
                  <td className={pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}>
                    {formatCurrency(pos.unrealized_pnl)}
                  </td>
                  <td className={pos.unrealized_pnl_pct >= 0 ? 'positive' : 'negative'}>
                    {formatPercent(pos.unrealized_pnl_pct)}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={7} className="loading">No positions - start trading!</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
