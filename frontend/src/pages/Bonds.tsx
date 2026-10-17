import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { t } from '../i18n'
import { usePriceStream } from '../hooks/usePriceStream'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import { bondsApi } from '../services/api'
import YieldCurveChart from '../components/charts/YieldCurveChart'

interface Bond {
  bond_id: string
  ticker: string
  name: string
  type: string
  coupon_rate: number
  face_value: number
  maturity_date: string
  remaining_days: number
  credit_rating: string
  yield_to_maturity: number
  price: number
  duration: number
  convexity: number
  spread: number
  accrued_interest: number
}

export default function Bonds() {
  const { worldId } = useCurrentWorld()
  const navigate = useNavigate()
  const [bonds, setBonds] = useState<Bond[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('ALL')
  const [yieldCurve, setYieldCurve] = useState<{ tenor: number; yield: number }[]>([])
  const [yieldLoading, setYieldLoading] = useState(true)
  const [yieldError, setYieldError] = useState<string | null>(null)
  const { prices, connected } = usePriceStream()

  useEffect(() => {
    const fetchBonds = async () => {
      try {
        const res = await axios.get(`/api/v1/bonds?world_id=${worldId}`)
        setBonds(res.data)
      } catch (err) {
        setError(t('common.dataError'))
      } finally {
        setLoading(false)
      }
    }
    fetchBonds()
  }, [worldId])

  // 收益率曲线：GET /bonds/yield-curve -> [{tenor, yield}]
  useEffect(() => {
    const fetchYieldCurve = async () => {
      try {
        const data = await bondsApi.getYieldCurve()
        setYieldCurve(Array.isArray(data) ? data : [])
        setYieldError(null)
      } catch {
        setYieldError(t('common.dataError'))
      } finally {
        setYieldLoading(false)
      }
    }
    fetchYieldCurve()
  }, [])

  const filtered = filter === 'ALL' ? bonds : bonds.filter(b => b.type === filter)
  const types = [...new Set(bonds.map(b => b.type))]

  const formatYield = (y: number) => `${(y * 100).toFixed(2)}%`
  const formatDate = (d: string) => new Date(d).toLocaleDateString('zh-CN')

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('bonds.title')}</h2>
          <p className="subtitle">{t('bonds.subtitle')}</p>
        </div>
        <div className="card"><div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('bonds.title')}</h2>
          <p className="subtitle">{t('bonds.subtitle')}</p>
        </div>
        <div className="card"><div className="error" style={{ padding: 40 }}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('bonds.title')}</h2>
        <p className="subtitle">
          {t('bonds.subtitle')} · {bonds.length} bonds
          <span style={{ marginLeft: 16, fontSize: 12, color: connected ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            ● {connected ? t('common.live') : t('common.connecting')}
          </span>
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('bonds.filter')}</span>
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
            {t('bonds.all')}
          </button>
          {types.map(type => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: '1px solid var(--border-color)',
                background: filter === type ? 'var(--accent-color)' : 'var(--bg-secondary)',
                color: filter === type ? 'white' : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('bonds.bondList')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('bonds.type')}</th>
              <th>{t('bonds.rating')}</th>
              <th>{t('bonds.coupon')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('bonds.ytm')}</th>
              <th>{t('bonds.duration')}</th>
              <th>{t('bonds.maturity')}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(bond => (
              <tr
                key={bond.bond_id}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/asset/${encodeURIComponent(bond.ticker)}`)}
                title={t('assetDetail.viewDetail')}
              >
                <td>{bond.ticker}</td>
                <td>{bond.name}</td>
                <td>{bond.type}</td>
                <td>
                  <span className={`tag ${bond.credit_rating === 'AAA' ? 'tag-green' : bond.credit_rating === 'BBB' ? 'tag-orange' : 'tag-red'}`}>
                    {bond.credit_rating}
                  </span>
                </td>
                <td>{formatYield(bond.coupon_rate)}</td>
                <td>
                  {(() => {
                    const live = prices.get(bond.ticker)
                    const dp = live ? live.price : bond.price
                    const ch = live ? live.changePct : 0
                    return (
                      <span style={{ color: ch >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontFamily: 'monospace' }}>
                        {dp.toFixed(2)}
                      </span>
                    )
                  })()}
                </td>
                <td className="positive">{formatYield(bond.yield_to_maturity)}</td>
                <td>{bond.duration.toFixed(1)}</td>
                <td>{formatDate(bond.maturity_date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('bonds.yieldCurve')}</span>
        </div>
        {yieldLoading ? (
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        ) : yieldError ? (
          <div className="error" style={{ padding: 40 }}>{yieldError}</div>
        ) : (
          <YieldCurveChart data={yieldCurve} height={260} />
        )}
      </div>
    </div>
  )
}
