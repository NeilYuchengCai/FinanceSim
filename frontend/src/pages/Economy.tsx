import { useState, useEffect } from 'react'
import axios from 'axios'
import MacroeconomicChart from '../components/charts/MacroeconomicChart'
import { t } from '../i18n'

interface MacroState {
  gdp_growth: number
  inflation: number
  unemployment: number
  interest_rate: number
  money_supply: number
  consumer_confidence: number
  industrial_production: number
  cycle_phase: string
  cycle_position: number
}

export default function Economy() {
  const [state, setState] = useState<MacroState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get('/api/economy/state')
        setState(res.data)
      } catch (err) {
        setError(t('common.dataError'))
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
          <h2>{t('economy.title')}</h2>
          <p className="subtitle">{t('economy.subtitle', '经济指标和趋势')}</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>{t('economy.title')}</h2>
          <p className="subtitle">{t('economy.subtitle', '经济指标和趋势')}</p>
        </div>
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  if (!state) return null

  const formatPercent = (v: number) => `${(v * 100).toFixed(2)}%`
  const formatIndex = (v: number) => v.toFixed(2)

  return (
    <div>
      <div className="page-header">
        <h2>{t('economy.title')}</h2>
        <p className="subtitle">{t('economy.subtitle', '经济指标和趋势')} - {t('overview.day', '第')} {state.cycle_position || 0} {t('overview.day', '天')}</p>
      </div>
      
      <div className="grid-3">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.gdp')}</span>
            <span className={`tag ${state.gdp_growth >= 0 ? 'tag-green' : 'tag-red'}`}>
              {(state.gdp_growth >= 0 ? '+' : '') + formatPercent(state.gdp_growth)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(state.gdp_growth)}</div>
          <div className="stat-change">{t('economy.annualRate', '年度增长率')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.cpi', 'CPI')}</span>
            <span className={`tag ${state.inflation <= 0.02 ? 'tag-green' : 'tag-red'}`}>
              {formatPercent(state.inflation)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(state.inflation)}</div>
          <div className="stat-change">{t('economy.target2pct', '目标: 2.0%')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.unemployment')}</span>
            <span className="tag tag-blue">{formatPercent(state.unemployment)}</span>
          </div>
          <div className="stat-value">{formatPercent(state.unemployment)}</div>
          <div className="stat-change">{t('economy.naturalRate5pct', '自然率: 5.0%')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.interestRate')}</span>
            <span className="tag tag-blue">{formatPercent(state.interest_rate)}</span>
          </div>
          <div className="stat-value">{formatPercent(state.interest_rate)}</div>
          <div className="stat-change">{t('economy.policyRate', '政策利率')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.consumerConfidence', '消费者信心')}</span>
          </div>
          <div className="stat-value">{formatIndex(state.consumer_confidence)}</div>
          <div className="stat-change">{t('economy.indexBase100', '基准指数: 100')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.industrialProduction', '工业生产')}</span>
          </div>
          <div className="stat-value">{formatIndex(state.industrial_production)}</div>
          <div className="stat-change">{t('economy.indexBase100', '基准指数: 100')}</div>
        </div>
      </div>

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">{t('economy.gdpTrend', 'GDP增长趋势')}</span>
        </div>
        <MacroeconomicChart
          data={[]}
          title="GDP Growth (%)"
          color="#ef4444"
          height={220}
        />
      </div>

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">{t('economy.inflationTrend', '通胀趋势')}</span>
        </div>
        <MacroeconomicChart
          data={[]}
          title="Inflation (%)"
          color="#f59e0b"
          height={220}
        />
      </div>
    </div>
  )
}
