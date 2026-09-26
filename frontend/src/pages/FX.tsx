import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'

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
    const fetchFX = async () => {
      try {
        const res = await axios.get('/api/v1/fx/pairs')
        setPairs(res.data)
      } catch (err) {
        setError(t('common.dataError'))
      } finally {
        setLoading(false)
      }
    }
    fetchFX()
  }, [])

  const formatChange = (change: number) => {
    const sign = change >= 0 ? '+' : ''
    return `${sign}${change.toFixed(3)}%`
  }

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('fx.title')}</h2>
          <p className="subtitle">{t('fx.subtitle', '货币对实时汇率')}</p>
        </div>
        <div className="card"><div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('fx.title')}</h2>
          <p className="subtitle">{t('fx.subtitle', '货币对实时汇率')}</p>
        </div>
        <div className="card"><div className="error" style={{ padding: 40 }}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('fx.title')}</h2>
        <p className="subtitle">{t('fx.subtitle', '货币对实时汇率')}</p>
      </div>

      <div className="grid-3">
        {pairs.map(pair => (
          <div key={pair.ticker} className="card">
            <div className="card-header">
              <span className="card-title">{pair.ticker}</span>
              <span className={`badge badge-dot ${pair.change_24h >= 0 ? 'green' : 'red'}`}></span>
            </div>
            <div className="stat-value">{pair.price.toFixed(4)}</div>
            <div className={`stat-change ${pair.change_24h >= 0 ? 'positive' : 'negative'}`}>
              {formatChange(pair.change_24h)}
            </div>
            <div className="stat-change">
              Spread: {pair.spread.toFixed(1)} pips | Vol: {(pair.volatility * 100).toFixed(2)}%
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('fx.allPairs', '全部货币对')}</span>
          <span className="tag tag-blue">{pairs.length} pairs</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('fx.base', '基准')}</th>
              <th>{t('fx.quote', '报价')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('fx.change24h', '24h涨跌')}</th>
              <th>{t('fx.spread', '点差')}</th>
              <th>{t('fx.high24h', '24h最高')}</th>
              <th>{t('fx.low24h', '24h最低')}</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map(pair => (
              <tr key={pair.ticker}>
                <td>{pair.ticker}</td>
                <td>{pair.base}</td>
                <td>{pair.quote}</td>
                <td>{pair.price.toFixed(4)}</td>
                <td className={pair.change_24h >= 0 ? 'positive' : 'negative'}>
                  {formatChange(pair.change_24h)}
                </td>
                <td>{pair.spread.toFixed(1)}</td>
                <td>{pair.high_24h.toFixed(4)}</td>
                <td>{pair.low_24h.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
