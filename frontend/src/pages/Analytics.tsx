import { useState, useEffect, useMemo } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import axios from 'axios'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'

const TRADING_DAYS = 252
const RISK_FREE_RATE = 0.02
const HISTORY_LIMIT = 90
const DEFAULT_TICKER = 'AAPL'
const CORRELATION_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'JPM', 'XOM']
// 下拉框里优先展示的知名标的，命中资产列表时才出现
const PREFERRED_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'JPM', 'XOM', 'SPY']
const ASSET_OPTION_COUNT = 20

const GREEN_RGB = '63, 185, 80'
const RED_RGB = '248, 81, 73'

const TOOLTIP_STYLE = { background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }
const TOOLTIP_LABEL_STYLE = { color: '#fff' }

const metricGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
  gap: 12,
}

const metricCardStyle: CSSProperties = {
  background: 'var(--bg-tertiary)',
  borderRadius: 6,
  padding: '10px 12px',
}

interface PricePoint {
  time: string
  close: number
}

interface CorrelationData {
  tickers: string[]
  matrix: number[][]
}

const pct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`

function toPercent(v: number) {
  return `${v.toFixed(2)}%`
}

function dirClass(v: number) {
  if (v > 0) return 'positive'
  if (v < 0) return 'negative'
  return ''
}

/** 卡片内容统一三态：加载中 / 错误 / 空数据 / 正常内容 */
function SectionBody({
  loading,
  error,
  empty,
  children,
}: {
  loading: boolean
  error: string | null
  empty: boolean
  children: ReactNode
}) {
  if (loading) return <div className="loading">{t('common.loading', '加载中...')}</div>
  if (error)
    return (
      <div className="error" style={{ color: 'var(--accent-red)', padding: 20 }}>
        {error}
      </div>
    )
  if (empty) return <div className="loading">{t('common.noData', '暂无数据')}</div>
  return <>{children}</>
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div style={metricCardStyle}>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      <div className={tone || undefined} style={{ fontSize: '1.15rem', fontWeight: 600 }}>
        {value}
      </div>
    </div>
  )
}

function CorrelationGrid({ data }: { data: CorrelationData }) {
  const tickers = data.tickers
  const matrix = data.matrix
  if (!tickers.length || !matrix.length) {
    return <div className="loading">{t('common.noData', '暂无数据')}</div>
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>{t('analytics.asset', '标的')}</th>
            {tickers.map((tk) => (
              <th key={tk} style={{ textAlign: 'center' }}>
                {tk}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickers.map((rowTicker, i) => (
            <tr key={rowTicker}>
              <td style={{ fontWeight: 600 }}>{rowTicker}</td>
              {tickers.map((colTicker, j) => {
                const raw = matrix[i] ? matrix[i][j] : undefined
                const v = typeof raw === 'number' && Number.isFinite(raw) ? raw : 0
                const alpha = 0.15 + 0.55 * Math.min(1, Math.abs(v))
                const background =
                  v >= 0 ? `rgba(${GREEN_RGB}, ${alpha})` : `rgba(${RED_RGB}, ${alpha})`
                return (
                  <td
                    key={colTicker}
                    style={{
                      textAlign: 'center',
                      background,
                      color: Math.abs(v) > 0.5 ? '#ffffff' : 'var(--text-primary)',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {v.toFixed(2)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Analytics() {
  const { worldId } = useCurrentWorld()
  const [tickerOptions, setTickerOptions] = useState<string[]>([DEFAULT_TICKER])
  const [selected, setSelected] = useState(DEFAULT_TICKER)

  const [prices, setPrices] = useState<PricePoint[]>([])
  const [pricesLoading, setPricesLoading] = useState(true)
  const [pricesError, setPricesError] = useState<string | null>(null)

  const [returns, setReturns] = useState<number[]>([])
  const [returnsLoading, setReturnsLoading] = useState(true)
  const [returnsError, setReturnsError] = useState<string | null>(null)

  const [correlation, setCorrelation] = useState<CorrelationData | null>(null)
  const [correlationLoading, setCorrelationLoading] = useState(true)
  const [correlationError, setCorrelationError] = useState<string | null>(null)

  // 资产列表：仅用于填充收益分析的下拉选择器
  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get('/api/v1/assets', {
          params: { world_id: worldId, type: 'EQUITY', limit: 500 },
        })
        const list: unknown[] = Array.isArray(res.data) ? res.data : []
        const all = list
          .map((a) => (a as { ticker?: unknown })?.ticker)
          .filter((tk): tk is string => typeof tk === 'string' && tk.length > 0)
        const preferred = PREFERRED_TICKERS.filter((tk) => all.includes(tk))
        const rest = all.filter((tk) => !preferred.includes(tk)).slice(0, ASSET_OPTION_COUNT)
        const merged = [...preferred, ...rest]
        setTickerOptions(merged.length ? merged : [DEFAULT_TICKER])
      } catch {
        // 资产列表拿不到时退化为默认标的，不阻塞价格/收益请求
        setTickerOptions([DEFAULT_TICKER])
      }
    }
    load()
  }, [worldId])

  // 价格历史：收益分析曲线 + 回撤分析共用同一份数据
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setPricesLoading(true)
      try {
        const res = await axios.get('/api/v1/assets/price-history', {
          params: { ticker: selected, world_id: worldId, limit: HISTORY_LIMIT },
        })
        if (cancelled) return
        const list: unknown[] = Array.isArray(res.data) ? res.data : []
        const points: PricePoint[] = []
        for (const item of list) {
          const p = item as { time?: unknown; close?: unknown }
          const close = Number(p?.close)
          if (Number.isFinite(close)) {
            points.push({ time: typeof p?.time === 'string' ? p.time : '', close })
          }
        }
        setPrices(points)
        setPricesError(null)
      } catch {
        if (!cancelled) setPricesError(t('common.dataError', '数据加载失败'))
      } finally {
        if (!cancelled) setPricesLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [selected, worldId])

  // 日收益率序列：风险指标计算用
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setReturnsLoading(true)
      try {
        const res = await axios.get(`/api/v1/analytics/returns/${encodeURIComponent(selected)}`, {
          params: { world_id: worldId },
        })
        if (cancelled) return
        const list: unknown[] = Array.isArray(res.data?.returns) ? res.data.returns : []
        setReturns(list.filter((v): v is number => typeof v === 'number' && Number.isFinite(v)))
        setReturnsError(null)
      } catch {
        if (!cancelled) setReturnsError(t('common.dataError', '数据加载失败'))
      } finally {
        if (!cancelled) setReturnsLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [selected, worldId])

  // 相关性矩阵：固定 6 只知名标的
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setCorrelationLoading(true)
      try {
        const res = await axios.get('/api/v1/analytics/correlation', {
          params: { world_id: worldId, tickers: CORRELATION_TICKERS.join(',') },
        })
        if (cancelled) return
        const tickers: unknown[] = Array.isArray(res.data?.tickers) ? res.data.tickers : []
        const matrix: unknown[] = Array.isArray(res.data?.matrix) ? res.data.matrix : []
        setCorrelation({
          tickers: tickers.filter((tk): tk is string => typeof tk === 'string'),
          matrix: matrix.map((row) =>
            Array.isArray(row)
              ? row.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0))
              : []
          ),
        })
        setCorrelationError(null)
      } catch {
        if (!cancelled) setCorrelationError(t('common.dataError', '数据加载失败'))
      } finally {
        if (!cancelled) setCorrelationLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [worldId])

  // 累计收益率序列（以首日收盘为基准 0）
  const cumulativeSeries = useMemo(() => {
    if (prices.length < 2) return []
    const base = prices[0].close
    if (!base) return []
    return prices.map((p) => ({
      date: p.time.slice(0, 10),
      cum: Number((((p.close / base) - 1) * 100).toFixed(4)),
    }))
  }, [prices])

  const performance = useMemo(() => {
    if (prices.length < 2) return null
    const base = prices[0].close
    const last = prices[prices.length - 1].close
    if (!base || !last) return null
    const total = (last / base - 1) * 100
    const years = (prices.length - 1) / TRADING_DAYS
    const annualized = years > 0 ? (Math.pow(last / base, 1 / years) - 1) * 100 : 0
    return { total, annualized }
  }, [prices])

  const riskMetrics = useMemo(() => {
    const n = returns.length
    if (n < 2) return null
    const mean = returns.reduce((a, b) => a + b, 0) / n
    const variance = returns.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1)
    const dailyStd = Math.sqrt(variance)
    const annualizedVol = dailyStd * Math.sqrt(TRADING_DAYS) * 100
    const annualizedRet = mean * TRADING_DAYS * 100
    const sharpe = annualizedVol > 0 ? (annualizedRet - RISK_FREE_RATE * 100) / annualizedVol : 0

    // 用收益率序列构造财富指数求最大回撤
    let wealth = 1
    let peak = 1
    let maxDd = 0
    for (const r of returns) {
      wealth *= 1 + r
      if (wealth > peak) peak = wealth
      const dd = wealth / peak - 1
      if (dd < maxDd) maxDd = dd
    }

    const sorted = [...returns].sort((a, b) => a - b)
    const varIndex = Math.min(sorted.length - 1, Math.max(0, Math.floor(0.05 * sorted.length)))
    const var95 = sorted[varIndex] * 100
    const positiveDays = (returns.filter((r) => r > 0).length / n) * 100

    return {
      annualizedVol,
      annualizedRet,
      sharpe,
      maxDrawdown: maxDd * 100,
      var95,
      positiveDays,
    }
  }, [returns])

  // 逐日回撤序列（相对历史最高点的跌幅，<= 0）
  const drawdownSeries = useMemo(() => {
    if (!prices.length) return []
    let peak = Number.NEGATIVE_INFINITY
    return prices.map((p) => {
      if (p.close > peak) peak = p.close
      const dd = peak ? (p.close / peak - 1) * 100 : 0
      return { date: p.time.slice(0, 10), dd: Number(dd.toFixed(4)) }
    })
  }, [prices])

  const worstDrawdown = useMemo(() => {
    if (!drawdownSeries.length) return null
    return drawdownSeries.reduce((worst, p) => (p.dd < worst.dd ? p : worst), drawdownSeries[0])
  }, [drawdownSeries])

  return (
    <div>
      <div className="page-header">
        <h2>{t('analytics.title', '分析')}</h2>
        <p className="subtitle">{t('analytics.subtitle', '深度数据分析')}</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.returnsAnalysis', '收益分析')}</span>
            <select
              className="input-field"
              style={{ width: 'auto', padding: '6px 10px' }}
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              aria-label={t('analytics.selectAsset', '选择标的')}
            >
              {tickerOptions.map((tk) => (
                <option key={tk} value={tk}>
                  {tk}
                </option>
              ))}
            </select>
          </div>
          <SectionBody
            loading={pricesLoading}
            error={pricesError}
            empty={cumulativeSeries.length === 0}
          >
            <>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={cumulativeSeries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} unit="%" />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      labelStyle={TOOLTIP_LABEL_STYLE}
                      formatter={(value) => `${Number(value).toFixed(2)}%`}
                    />
                    <Line
                      type="monotone"
                      dataKey="cum"
                      stroke="#58a6ff"
                      strokeWidth={2}
                      dot={false}
                      name={t('analytics.cumulativeReturn', '累计收益率')}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              {performance && (
                <div style={{ ...metricGridStyle, marginTop: 12 }}>
                  <Metric
                    label={t('analytics.totalReturn', '区间总收益率')}
                    value={pct(performance.total)}
                    tone={dirClass(performance.total)}
                  />
                  <Metric
                    label={t('analytics.annualizedReturn', '年化收益率')}
                    value={pct(performance.annualized)}
                    tone={dirClass(performance.annualized)}
                  />
                </div>
              )}
            </>
          </SectionBody>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.riskMetrics', '风险指标')}</span>
            <span className="tag tag-gray">{selected}</span>
          </div>
          <SectionBody
            loading={returnsLoading}
            error={returnsError}
            empty={!riskMetrics}
          >
            <>
              <div style={metricGridStyle}>
                <Metric
                  label={t('analytics.annualizedVolatility', '年化波动率')}
                  value={toPercent(riskMetrics?.annualizedVol ?? 0)}
                />
                <Metric
                  label={t('analytics.sharpeRatio', '夏普比率')}
                  value={(riskMetrics?.sharpe ?? 0).toFixed(2)}
                  tone={dirClass(riskMetrics?.sharpe ?? 0)}
                />
                <Metric
                  label={t('analytics.maxDrawdown', '最大回撤')}
                  value={toPercent(riskMetrics?.maxDrawdown ?? 0)}
                  tone="negative"
                />
                <Metric
                  label={t('analytics.var95', '95% 单日 VaR')}
                  value={toPercent(riskMetrics?.var95 ?? 0)}
                  tone="negative"
                />
                <Metric
                  label={t('analytics.positiveDays', '正收益天数占比')}
                  value={toPercent(riskMetrics?.positiveDays ?? 0)}
                />
              </div>
              <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
                {t('analytics.riskFreeRate', '无风险利率')} 2% · {t('analytics.sampleDays', '样本天数')}{' '}
                {returns.length}
              </div>
            </>
          </SectionBody>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.correlationMatrix', '相关性矩阵')}</span>
            <span className="tag tag-blue">{CORRELATION_TICKERS.join(' · ')}</span>
          </div>
          <SectionBody
            loading={correlationLoading}
            error={correlationError}
            empty={!correlation || !correlation.tickers.length || !correlation.matrix.length}
          >
            <CorrelationGrid data={correlation as CorrelationData} />
          </SectionBody>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.drawdownAnalysis', '回撤分析')}</span>
            <span className="tag tag-gray">{selected}</span>
          </div>
          <SectionBody
            loading={pricesLoading}
            error={pricesError}
            empty={drawdownSeries.length === 0}
          >
            <>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={drawdownSeries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} unit="%" />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      labelStyle={TOOLTIP_LABEL_STYLE}
                      formatter={(value) => `${Number(value).toFixed(2)}%`}
                    />
                    <Area
                      type="monotone"
                      dataKey="dd"
                      stroke="#f85149"
                      fill="rgba(248, 81, 73, 0.35)"
                      strokeWidth={2}
                      name={t('analytics.drawdownPct', '回撤')}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {worstDrawdown && (
                <div style={{ ...metricGridStyle, marginTop: 12 }}>
                  <Metric
                    label={t('analytics.maxDrawdown', '最大回撤')}
                    value={toPercent(worstDrawdown.dd)}
                    tone="negative"
                  />
                  <Metric
                    label={t('analytics.maxDrawdownDate', '发生日期')}
                    value={worstDrawdown.date || '—'}
                  />
                </div>
              )}
            </>
          </SectionBody>
        </div>
      </div>
    </div>
  )
}
