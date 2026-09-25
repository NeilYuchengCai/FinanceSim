import { useState, useEffect } from 'react'
import axios from 'axios'

interface Bond {
  bond_id: string
  ticker: string
  name: string
  type: string
  credit_rating: string
  maturity_date: string
  coupon_rate: number
  face_value: number
  current_price: number
  yield_to_maturity: number
  duration: number
  convexity: number
  spread: number
}

interface YieldPoint {
  tenor: string
  yield: number
}

export default function Bonds() {
  const [bonds, setBonds] = useState<Bond[]>([])
  const [yieldCurve, setYieldCurve] = useState<YieldPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bondsRes, curveRes] = await Promise.all([
          axios.get('/api/bonds'),
          axios.get('/api/bonds/yield-curve')
        ])
        setBonds(bondsRes.data || [])
        setYieldCurve(curveRes.data || [])
      } catch (err) {
        setError('Failed to load bond data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const filteredBonds = filter === 'ALL' ? bonds : bonds.filter(b => b.type === filter)

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>Bonds</h2>
          <p className="subtitle">Government and corporate bonds</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading bond data...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>Bonds</h2>
          <p className="subtitle">Government and corporate bonds</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>Bonds</h2>
        <p className="subtitle">Government and corporate bonds</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Yield Curve</span>
        </div>
        <div className="chart-container" style={{height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          {yieldCurve.length > 0 ? (
            <table className="data-table" style={{fontSize: 12}}>
              <thead>
                <tr>
                  <th>Tenor</th>
                  <th>Yield (%)</th>
                </tr>
              </thead>
              <tbody>
                {yieldCurve.slice(0, 10).map((point, i) => (
                  <tr key={i}>
                    <td>{point.tenor}</td>
                    <td>{point.yield.toFixed(3)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <span className="loading">No yield curve data</span>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Bond List</span>
          <select
            className="input-field"
            style={{ width: 'auto' }}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="ALL">All</option>
            <option value="UST">Treasury</option>
            <option value="IG">Investment Grade</option>
            <option value="HY">High Yield</option>
          </select>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Type</th>
              <th>Rating</th>
              <th>Coupon</th>
              <th>Price</th>
              <th>YTM</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {filteredBonds.length > 0 ? (
              filteredBonds.map(bond => (
                <tr key={bond.bond_id}>
                  <td><strong>{bond.ticker}</strong></td>
                  <td>{bond.name}</td>
                  <td>
                    <span className={`tag ${bond.type === 'UST' ? 'tag-blue' : bond.type === 'IG' ? 'tag-green' : 'tag-orange'}`}>
                      {bond.type}
                    </span>
                  </td>
                  <td>{bond.credit_rating}</td>
                  <td>{(bond.coupon_rate * 100).toFixed(2)}%</td>
                  <td>${bond.current_price.toFixed(2)}</td>
                  <td>{(bond.yield_to_maturity * 100).toFixed(2)}%</td>
                  <td>{bond.duration.toFixed(2)}yr</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={8} className="loading">No bonds found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
