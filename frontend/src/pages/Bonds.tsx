import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'

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
  const [bonds, setBonds] = useState<Bond[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    const fetchBonds = async () => {
      try {
        const res = await axios.get('/api/v1/bonds?world_id=1')
        setBonds(res.data)
      } catch (err) {
        setError(t('common.dataError'))
      } finally {
        setLoading(false)
      }
    }
    fetchBonds()
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
          <p className="subtitle">{t('bonds.subtitle', '国债和企业债')}</p>
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
          <p className="subtitle">{t('bonds.subtitle', '国债和企业债')}</p>
        </div>
        <div className="card"><div className="error" style={{ padding: 40 }}>{error}</div></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('bonds.title')}</h2>
        <p className="subtitle">{t('bonds.subtitle', '国债和企业债')} · {bonds.length} bonds</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('bonds.filter', '筛选')}</span>
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
            {t('bonds.all', '全部')}
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
          <span className="card-title">{t('bonds.bondList', '债券列表')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('bonds.type', '类型')}</th>
              <th>{t('bonds.rating')}</th>
              <th>{t('bonds.coupon')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('bonds.ytm', '到期收益率')}</th>
              <th>{t('bonds.duration')}</th>
              <th>{t('bonds.maturity', '到期日')}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(bond => (
              <tr key={bond.bond_id}>
                <td>{bond.ticker}</td>
                <td>{bond.name}</td>
                <td>{bond.type}</td>
                <td>
                  <span className={`tag ${bond.credit_rating === 'AAA' ? 'tag-green' : bond.credit_rating === 'BBB' ? 'tag-orange' : 'tag-red'}`}>
                    {bond.credit_rating}
                  </span>
                </td>
                <td>{formatYield(bond.coupon_rate)}</td>
                <td>{bond.price.toFixed(2)}</td>
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
        <div className="chart-container" style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>📈</div>
            <div>Yield Curve: {formatYield(bonds[0]?.yield_to_maturity || 0)} - {formatYield(bonds[bonds.length - 1]?.yield_to_maturity || 0)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
