import { useState, useEffect } from 'react'
import axios from 'axios'

interface FXPair {
  ticker: string
  base: string
  quote: string
  price: number
  spread: number
  volatility: number
  change_24h: number
  high_24h: number
  low_24h: number
}

export default function FX() {
  const [pairs, setPairs] = useState<FXPair[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get('/api/fx/pairs')
        setPairs(res.data || [])
      } catch (err) {
        setError('Failed to load FX data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const formatPrice = (v: number) => {
    if (v > 10) return v.toFixed(3)
    return v.toFixed(5)
  }

  const formatChange = (v: number) => {
    const sign = v >= 0 ? '+' : ''
    return `${sign}${(v * 100).toFixed(3)}%`
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>FX</h2>
          <p className="subtitle">Foreign exchange markets</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading FX data...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>FX</h2>
          <p className="subtitle">Foreign exchange markets</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>FX</h2>
        <p className="subtitle">Foreign exchange markets</p>
      </div>

      <div className="grid-3">
        {pairs.map(pair => (
          <div key={pair.ticker} className="card">
            <div className="card-header">
              <span className="card-title">{pair.ticker}</span>
              <span className={`badge badge-dot ${pair.change_24h >= 0 ? 'green' : 'red'}`}></span>
            </div>
            <div className="stat-value">{formatPrice(pair.price)}</div>
            <div className={`stat-change ${pair.change_24h >= 0 ? 'positive' : 'negative'}`}>
              {formatChange(pair.change_24h)}
            </div>
            <div className="stat-change">
              Spread: {pair.spread} pips | Vol: {pair.volatility}%
            </div>
            <div className="stat-change" style={{fontSize: 11}}>
              H: {formatPrice(pair.high_24h)} L: {formatPrice(pair.low_24h)}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Cross Rates</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Pair</th>
              <th>Base</th>
              <th>Quote</th>
              <th>Price</th>
              <th>24h Change</th>
              <th>Spread (pips)</th>
              <th>Volatility</th>
              <th>High 24h</th>
              <th>Low 24h</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map(pair => (
              <tr key={pair.ticker}>
                <td><strong>{pair.ticker}</strong></td>
                <td>{pair.base}</td>
                <td>{pair.quote}</td>
                <td>{formatPrice(pair.price)}</td>
                <td className={pair.change_24h >= 0 ? 'positive' : 'negative'}>
                  {formatChange(pair.change_24h)}
                </td>
                <td>{pair.spread}</td>
                <td>{pair.volatility}%</td>
                <td>{formatPrice(pair.high_24h)}</td>
                <td>{formatPrice(pair.low_24h)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
