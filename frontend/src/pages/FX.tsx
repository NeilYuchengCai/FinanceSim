import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { t } from '../i18n'
import { usePriceStream, usePriceStreamPaused } from '../hooks/usePriceStream'

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

// 外汇对ticker映射到统一的WS ticker格式 (EUR/USD -> EURUSD)
function normalizeTicker(ticker: string): string {
  return ticker.replace('/', '')
}

export default function FX() {
  const navigate = useNavigate()
  const [pairs, setPairs] = useState<FXPair[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { prices, connected } = usePriceStream()
  const paused = usePriceStreamPaused()

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

  const formatPrice = (price: number) => price.toFixed(4)

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('fx.title')}</h2>
          <p className="subtitle">{t('fx.subtitle')}</p>
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
          <p className="subtitle">{t('fx.subtitle')}</p>
        </div>
        <div className="card"><div className="error" style={{ padding: 40 }}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('fx.title')}</h2>
        <p className="subtitle">
          {t('fx.subtitle')} · {pairs.length} pairs
          <span style={{ marginLeft: 16, fontSize: 12, color: paused ? 'var(--accent-amber, #e0a73c)' : connected ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            ● {paused ? t('common.paused') : connected ? t('common.live') : t('common.connecting')}
          </span>
        </p>
      </div>

      <div className="grid-3">
        {pairs.map(pair => {
          const wsTicker = normalizeTicker(pair.ticker)
          const quote = prices.get(wsTicker)
          const displayPrice = quote ? quote.price : pair.price
          const displayChange = quote ? quote.changePct : pair.change_24h

          return (
            <div
              key={pair.ticker}
              className="card"
              style={{ borderLeft: `3px solid ${displayChange >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}`, cursor: 'pointer' }}
              onClick={() => navigate(`/asset/${encodeURIComponent(pair.ticker)}`)}
              title={t('assetDetail.viewDetail')}
            >
              <div className="card-header">
                <span className="card-title">{pair.ticker}</span>
                <span className={`badge badge-dot ${displayChange >= 0 ? 'green' : 'red'}`}></span>
              </div>
              <div className="stat-value" style={{ fontFamily: 'monospace' }}>
                {formatPrice(displayPrice)}
              </div>
              <div className={`stat-change ${displayChange >= 0 ? 'positive' : 'negative'}`}>
                {formatChange(displayChange)}
              </div>
              <div className="stat-change" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                Spread: {pair.spread.toFixed(1)} pips | Vol: {(pair.volatility * 100).toFixed(2)}%
              </div>
            </div>
          )
        })}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('fx.allPairs')}</span>
          <span className="tag tag-blue">{pairs.length} pairs</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('fx.base')}</th>
              <th>{t('fx.quote')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('fx.change24h')}</th>
              <th>{t('fx.spread')}</th>
              <th>{t('fx.high24h')}</th>
              <th>{t('fx.low24h')}</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map(pair => {
              const wsTicker = normalizeTicker(pair.ticker)
              const quote = prices.get(wsTicker)
              const displayPrice = quote ? quote.price : pair.price
              const displayChange = quote ? quote.changePct : pair.change_24h

              return (
                <tr
                  key={pair.ticker}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/asset/${encodeURIComponent(pair.ticker)}`)}
                  title={t('assetDetail.viewDetail')}
                >
                  <td>{pair.ticker}</td>
                  <td>{pair.base}</td>
                  <td>{pair.quote}</td>
                  <td style={{ fontFamily: 'monospace' }}>{formatPrice(displayPrice)}</td>
                  <td className={displayChange >= 0 ? 'positive' : 'negative'}>
                    {formatChange(displayChange)}
                  </td>
                  <td>{pair.spread.toFixed(1)}</td>
                  <td>{pair.high_24h.toFixed(4)}</td>
                  <td>{pair.low_24h.toFixed(4)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
