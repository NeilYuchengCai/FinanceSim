import { useState, useEffect } from 'react'
import axios from 'axios'
import MacroeconomicChart from '../components/charts/MacroeconomicChart'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'

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

/** /economy/history 的单条记录（容忍后端字段演进，见 mapHistory） */
interface HistoryRow {
  day?: unknown
  days_since_start?: unknown
  cycle_position?: unknown
  gdp_growth?: unknown
  inflation?: unknown
}

interface HistoryPoint {
  day: number
  gdpGrowthPct: number
  inflationPct: number
}

/** /economy/indicators 的综合指标（字段全部可选，缺字段时跳过该行） */
interface EconomicIndicators {
  growth_indicators?: {
    gdp_growth_annual?: number
    industrial_production_index?: number
    consumer_confidence?: number
  }
  inflation_indicators?: {
    cpi_inflation?: number
    expected_inflation?: number
  }
  labor_market?: {
    unemployment_rate?: number
    natural_rate?: number
  }
  monetary_policy?: {
    policy_rate?: number
    money_supply_growth?: number
  }
  business_cycle?: {
    phase?: string
    position?: number
    days_in_cycle?: number
  }
}

/**
 * 将 /economy/history 映射为图表数据。
 * 引擎内宏观指标以小数存储（0.03 = 3%），与 /economy/state 卡片同一口径，统一换算为百分数。
 * day 字段按 day -> days_since_start -> cycle_position -> 序号 的顺序容错取值，
 * 后端若改从 DB 读取且保持字段兼容，此处无需改动。
 */
function mapHistory(raw: unknown): HistoryPoint[] {
  if (!Array.isArray(raw)) return []
  const points: HistoryPoint[] = []
  raw.forEach((item, index) => {
    if (typeof item !== 'object' || item === null) return
    const row = item as HistoryRow
    const dayRaw = row.day ?? row.days_since_start ?? row.cycle_position ?? index + 1
    const day = Number(dayRaw)
    const gdp = Number(row.gdp_growth)
    const inflation = Number(row.inflation)
    points.push({
      day: Number.isFinite(day) ? day : index + 1,
      gdpGrowthPct: Number.isFinite(gdp) ? gdp * 100 : 0,
      inflationPct: Number.isFinite(inflation) ? inflation * 100 : 0,
    })
  })
  return points
}

export default function Economy() {
  const { worldId } = useCurrentWorld()
  const [state, setState] = useState<MacroState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState<string | null>(null)

  const [indicators, setIndicators] = useState<EconomicIndicators | null>(null)
  const [indicatorsLoading, setIndicatorsLoading] = useState(true)
  const [indicatorsError, setIndicatorsError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get('/api/v1/economy/state')
        setState(res.data)
      } catch (err) {
        setError(t('common.dataError'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        // world_id 必填：后端 /history 已改为按世界读 macro_snapshots 表；
        // 旧版本忽略额外 query 参数，传 world_id 对两者都兼容
        const res = await axios.get('/api/v1/economy/history', {
          params: { world_id: worldId, limit: 100 },
        })
        setHistory(mapHistory(res.data))
        setHistoryError(null)
      } catch {
        setHistoryError(t('common.dataError'))
      } finally {
        setHistoryLoading(false)
      }
    }
    fetchHistory()
  }, [worldId])

  useEffect(() => {
    const fetchIndicators = async () => {
      try {
        const res = await axios.get<EconomicIndicators>('/api/v1/economy/indicators')
        setIndicators(res.data && typeof res.data === 'object' ? res.data : null)
        setIndicatorsError(null)
      } catch {
        setIndicatorsError(t('economy.indicatorsFailed'))
      } finally {
        setIndicatorsLoading(false)
      }
    }
    fetchIndicators()
  }, [])

  const header = (
    <div className="page-header">
      <h2>{t('economy.title')}</h2>
      <p className="subtitle">
        {t('economy.subtitle')} - {t('overview.day')} {state?.cycle_position || 0} {t('overview.day')}
      </p>
    </div>
  )

  if (loading) {
    return (
      <div>
        {header}
        <div className="card"><div className="loading" style={{padding: 40}}>{t('common.loading')}</div></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        {header}
        <div className="card"><div className="error" style={{padding: 40}}>{error}</div></div>
      </div>
    )
  }

  if (!state) return null

  const formatPercent = (v: number) => `${(v * 100).toFixed(2)}%`
  const formatIndex = (v: number) => v.toFixed(2)
  // /indicators 忠实透传：注意后端该接口单位不完全一致
  // （gdp_growth_annual / cpi_inflation / policy_rate / unemployment_rate 为百分数，
  //  expected_inflation / natural_rate 为小数），此处不做猜测性换算，待后端统一单位。
  const formatPctNumber = (v: number) => `${v.toFixed(2)}%`

  const gdpSeries = history.map((point) => ({ day: point.day, value: Number(point.gdpGrowthPct.toFixed(4)) }))
  const inflationSeries = history.map((point) => ({ day: point.day, value: Number(point.inflationPct.toFixed(4)) }))

  const chartPlaceholder = (
    <div className="loading" style={{ padding: 40 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>📉</div>
        <div>{t('economy.noHistory')}</div>
        <div style={{ fontSize: 12, marginTop: 6, color: 'var(--text-secondary)' }}>
          {t('economy.noHistoryHint')}
        </div>
      </div>
    </div>
  )

  const indicatorRows: { label: string; value: string }[] = []
  if (indicators) {
    const g = indicators.growth_indicators ?? {}
    const inf = indicators.inflation_indicators ?? {}
    const labor = indicators.labor_market ?? {}
    const money = indicators.monetary_policy ?? {}
    const cycle = indicators.business_cycle ?? {}
    if (typeof g.gdp_growth_annual === 'number') {
      indicatorRows.push({ label: t('economy.indGdpGrowthAnnual'), value: formatPctNumber(g.gdp_growth_annual) })
    }
    if (typeof g.industrial_production_index === 'number') {
      indicatorRows.push({ label: t('economy.indIndustrialProduction'), value: formatIndex(g.industrial_production_index) })
    }
    if (typeof g.consumer_confidence === 'number') {
      indicatorRows.push({ label: t('economy.indConsumerConfidence'), value: formatIndex(g.consumer_confidence) })
    }
    if (typeof inf.cpi_inflation === 'number') {
      indicatorRows.push({ label: t('economy.indCpiInflation'), value: formatPctNumber(inf.cpi_inflation) })
    }
    if (typeof inf.expected_inflation === 'number') {
      indicatorRows.push({ label: t('economy.indExpectedInflation'), value: formatPctNumber(inf.expected_inflation) })
    }
    if (typeof labor.unemployment_rate === 'number') {
      indicatorRows.push({ label: t('economy.indUnemploymentRate'), value: formatPctNumber(labor.unemployment_rate) })
    }
    if (typeof labor.natural_rate === 'number') {
      indicatorRows.push({ label: t('economy.indNaturalRate'), value: formatPctNumber(labor.natural_rate) })
    }
    if (typeof money.policy_rate === 'number') {
      indicatorRows.push({ label: t('economy.indPolicyRate'), value: formatPctNumber(money.policy_rate) })
    }
    if (typeof money.money_supply_growth === 'number') {
      indicatorRows.push({ label: t('economy.indMoneySupplyGrowth'), value: formatPctNumber(money.money_supply_growth) })
    }
    if (typeof cycle.phase === 'string') {
      indicatorRows.push({ label: t('economy.indCyclePhase'), value: cycle.phase })
    }
    if (typeof cycle.position === 'number') {
      indicatorRows.push({ label: t('economy.indCyclePosition'), value: String(cycle.position) })
    }
    if (typeof cycle.days_in_cycle === 'number') {
      indicatorRows.push({ label: t('economy.indDaysInCycle'), value: String(cycle.days_in_cycle) })
    }
  }

  return (
    <div>
      {header}

      <div className="grid-3">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.gdp')}</span>
            <span className={`tag ${state.gdp_growth >= 0 ? 'tag-green' : 'tag-red'}`}>
              {(state.gdp_growth >= 0 ? '+' : '') + formatPercent(state.gdp_growth)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(state.gdp_growth)}</div>
          <div className="stat-change">{t('economy.annualRate')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.cpi')}</span>
            <span className={`tag ${state.inflation <= 0.02 ? 'tag-green' : 'tag-red'}`}>
              {formatPercent(state.inflation)}
            </span>
          </div>
          <div className="stat-value">{formatPercent(state.inflation)}</div>
          <div className="stat-change">{t('economy.target2pct')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.unemployment')}</span>
            <span className="tag tag-blue">{formatPercent(state.unemployment)}</span>
          </div>
          <div className="stat-value">{formatPercent(state.unemployment)}</div>
          <div className="stat-change">{t('economy.naturalRate5pct')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.interestRate')}</span>
            <span className="tag tag-blue">{formatPercent(state.interest_rate)}</span>
          </div>
          <div className="stat-value">{formatPercent(state.interest_rate)}</div>
          <div className="stat-change">{t('economy.policyRate')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.consumerConfidence')}</span>
          </div>
          <div className="stat-value">{formatIndex(state.consumer_confidence)}</div>
          <div className="stat-change">{t('economy.indexBase100')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('economy.industrialProduction')}</span>
          </div>
          <div className="stat-value">{formatIndex(state.industrial_production)}</div>
          <div className="stat-change">{t('economy.indexBase100')}</div>
        </div>
      </div>

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">{t('economy.gdpTrend')}</span>
        </div>
        {historyLoading ? (
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        ) : historyError ? (
          <div className="error" style={{ padding: 40 }}>{historyError}</div>
        ) : gdpSeries.length > 0 ? (
          <MacroeconomicChart
            data={gdpSeries}
            title={t('economy.gdpGrowthPercent')}
            color="#ef4444"
            height={220}
          />
        ) : (
          chartPlaceholder
        )}
      </div>

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">{t('economy.inflationTrend')}</span>
        </div>
        {historyLoading ? (
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        ) : historyError ? (
          <div className="error" style={{ padding: 40 }}>{historyError}</div>
        ) : inflationSeries.length > 0 ? (
          <MacroeconomicChart
            data={inflationSeries}
            title={t('economy.inflationPercent')}
            color="#f59e0b"
            height={220}
          />
        ) : (
          chartPlaceholder
        )}
      </div>

      <div className="card" style={{marginTop: 16}}>
        <div className="card-header">
          <span className="card-title">{t('economy.indicators')}</span>
        </div>
        {indicatorsLoading ? (
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        ) : indicatorsError ? (
          <div className="error" style={{ padding: 40 }}>{indicatorsError}</div>
        ) : indicatorRows.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            {t('common.noData')}
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('simulation.metric')}</th>
                <th>{t('markets.price')}</th>
              </tr>
            </thead>
            <tbody>
              {indicatorRows.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td>{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
