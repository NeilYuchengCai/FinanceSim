import { useState, useEffect } from 'react'
import axios from 'axios'
import MacroeconomicChart from '../components/charts/MacroeconomicChart'

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

interface EconomicIndicator {
  growth_indicators: Record<string, number>
  inflation_indicators: Record<string, number>
  labor_market: Record<string, number>
  monetary_policy: Record<string, number>
  business_cycle: Record<string, any>
}

export default function Economy() {
  const [state, setState] = useState<MacroState | null>(null)
  const [indicators, setIndicators] = useState<EconomicIndicator | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stateRes, indicatorsRes, historyRes] = await Promise.all([
          axios.get('/api/economy/state'),
          axios.get('/api/economy/indicators'),
          axios.get('/api/economy/history?limit=50')
        ])
        setState(stateRes.data)
        setIndicators(indicatorsRes.data)
        setHistory(historyRes.data || [])
      } catch (err) {
        setError('Failed to load economy data')
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
          <h2>Economy</h2>
          <p className="subtitle">Macroeconomic indicators</p>
        </div>
        <div className="card"><div className="loading" style={{padding: 40}}>Loading economy data...</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <h2>Economy</h2>
          <p className="subtitle">Macroeconomic indicators</p>
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
        <h2>Economy</h2>
        <p className="subtitle">Macroeconomic indicators - Day {state.cycle_position || 0}</p>
      </div>
      
      <div className="grid-3">
        <div className="card">
          <div className="card-header">
            <span className="card-title">GDP Growth</span>
            <span className={`tag ${state.gdp_growth >= 0 ? 'tag-green' : 'tag-red'}`}>
              {(state.gdp_growth >= 0 ? '+' : '') + formatPercent(state.gdp_growth)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(state.gdp_growth)}</div>
          <div className="stat-change">Annual rate</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Inflation (CPI)</span>
            <span className={`tag ${state.inflation <= 0.02 ? 'tag-green' : 'tag-red'}`}>
              {formatPercent(state.inflation)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(state.inflation)}</div>
          <div className="stat-change">Target: 2.0%</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Unemployment</span>
            <span className="tag tag-blue">{formatPercent(state.unemployment)}</span>
          </div>
          <div className="stat-value">{formatPercent(state.unemployment)}</div>
          <div className="stat-change">Natural rate: 5.0%</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Interest Rate</span>
            <span className="tag tag-blue">{formatPercent(state.interest_rate)}</span>
          </div>
          <div className="stat-value">{formatPercent(state.interest_rate)}</div>
          <div className="stat-change">Policy rate</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Consumer Confidence</span>
          </div>
          <div className="stat-value">{formatIndex(state.consumer_confidence)}</div>
          <div className="stat-change">Index (base 100)</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Industrial Production</span>
          </div>
          <div className="stat-value">{formatIndex(state.industrial_production)}</div>
          <div className="stat-change">Index (base 100)</div>
        </div>
      </div>

      {indicators && (
        <div className="grid-2">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Business Cycle</span>
              <span className="tag tag-purple">{indicators.business_cycle.phase}</span>
            </div>
            <div style={{padding: 20}}>
              <div style={{marginBottom: 12}}>
                <span style={{color: 'var(--text-secondary)'}}>Phase: </span>
                <strong>{indicators.business_cycle.phase}</strong>
              </div>
              <div style={{marginBottom: 12}}>
                <span style={{color: 'var(--text-secondary)'}}>Position: </span>
                <strong>{indicators.business_cycle.position}</strong>
              </div>
              <div>
                <span style={{color: 'var(--text-secondary)'}}>Days in cycle: </span>
                <strong>{indicators.business_cycle.days_in_cycle}</strong>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Monetary Policy</span>
            </div>
            <div style={{padding: 20}}>
              <div style={{marginBottom: 12}}>
                <span style={{color: 'var(--text-secondary)'}}>Policy Rate: </span>
                <strong>{indicators.monetary_policy.policy_rate.toFixed(2)}%</strong>
              </div>
              <div style={{marginBottom: 12}}>
                <span style={{color: 'var(--text-secondary)'}}>Money Supply Growth: </span>
                <strong>{indicators.monetary_policy.money_supply_growth.toFixed(2)}%</strong>
              </div>
              <div>
                <span style={{color: 'var(--text-secondary)'}}>Expected Inflation: </span>
                <strong>{indicators.inflation_indicators.expected_inflation.toFixed(2)}%</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">GDP Growth Trend</span>
        </div>
        <MacroeconomicChart
          data={history.map(h => ({ day: h.days_since_start || 0, value: h.gdp_growth * 100 }))}
          title="GDP Growth (%)"
          color="#ef4444"
          height={220}
        />
      </div>

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">Inflation Trend</span>
        </div>
        <MacroeconomicChart
          data={history.map(h => ({ day: h.days_since_start || 0, value: h.inflation * 100 }))}
          title="Inflation (%)"
          color="#f59e0b"
          height={220}
        />
      </div>
    </div>
  )
}
