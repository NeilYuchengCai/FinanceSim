import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { t, formatCurrency } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import { usePriceStream } from '../hooks/usePriceStream'
import PieChartComponent from '../components/charts/PieChartComponent'

/**
 * 投资组合页（P0-1 重写）
 *
 * 数据契约（已与后端核对）：
 * - GET /api/v1/trading/portfolio?world_id={worldId}
 *   -> { cash, total_value, total_invested, total_realized_pnl, unrealized_pnl, net_worth }
 * - GET /api/v1/trading/portfolio/positions?world_id={worldId}
 *   -> [{ ticker, quantity, avg_price, last_price, market_value, cost_basis,
 *         unrealized_pnl, realized_pnl, pnl_percent }]
 */

interface PortfolioSummary {
  cash: number
  total_value: number
  total_invested: number
  total_realized_pnl: number
  unrealized_pnl: number
  net_worth: number
}

interface Position {
  ticker: string
  quantity: number
  avg_price: number
  last_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  realized_pnl: number
  pnl_percent: number
}

interface PositionRow {
  position: Position
  /** 实时行情存在时覆盖 last_price，否则用接口返回值 */
  displayPrice: number
  marketValue: number
  unrealizedPnl: number
  pnlPercent: number
}

interface WorldInfo {
  id: number
  name: string
  // 后端契约：WorldResponse 目前未返回该字段，暴露后自动生效（存在就用）
  starting_capital?: number
}

// 后端 /worlds/{id} 未返回 starting_capital 时，按后端 WorldCreate 默认初始资金计算
const FALLBACK_STARTING_CAPITAL = 100000

const money = (v: number) => formatCurrency(Number.isFinite(v) ? v : 0)
const pct = (v: number) => `${(Number.isFinite(v) ? v : 0).toFixed(2)}%`

export default function Portfolio() {
  const { worldId } = useCurrentWorld()
  const { prices } = usePriceStream()
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [startingCapital, setStartingCapital] = useState(FALLBACK_STARTING_CAPITAL)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // 世界信息独立容错：失败不影响组合数据展示，收益率回落默认初始资金
      const [summaryRes, positionsRes, worldRes] = await Promise.all([
        axios.get<PortfolioSummary>(`/api/v1/trading/portfolio?world_id=${worldId}`),
        axios.get<Position[]>(`/api/v1/trading/portfolio/positions?world_id=${worldId}`),
        axios.get<WorldInfo>(`/api/v1/worlds/${worldId}`).catch(() => null),
      ])
      setSummary(summaryRes.data)
      setPositions(Array.isArray(positionsRes.data) ? positionsRes.data : [])
      const worldStartingCapital = worldRes?.data?.starting_capital
      setStartingCapital(
        typeof worldStartingCapital === 'number' && worldStartingCapital > 0
          ? worldStartingCapital
          : FALLBACK_STARTING_CAPITAL,
      )
    } catch {
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
  }, [worldId])

  useEffect(() => {
    load()
  }, [load])

  // 实时行情叠加：WS 有最新价时覆盖 现价/市值/未实现盈亏/盈亏%，否则用接口快照
  const rows: PositionRow[] = positions.map((position) => {
    const live = prices.get(position.ticker)
    if (!live) {
      return {
        position,
        displayPrice: position.last_price,
        marketValue: position.market_value,
        unrealizedPnl: position.unrealized_pnl,
        pnlPercent: position.pnl_percent,
      }
    }
    const price = live.price
    return {
      position,
      displayPrice: price,
      marketValue: price * position.quantity,
      unrealizedPnl: (price - position.avg_price) * position.quantity,
      pnlPercent:
        position.avg_price > 0 ? ((price - position.avg_price) / position.avg_price) * 100 : 0,
    }
  })

  // 资产配置饼图：按（实时）市值占比
  const allocation = rows
    .filter((row) => row.marketValue > 0)
    .map((row) => ({
      name: row.position.ticker,
      value: Number(row.marketValue.toFixed(2)),
    }))

  const totalReturnPct =
    summary && summary.net_worth !== undefined && startingCapital > 0
      ? ((summary.net_worth - startingCapital) / startingCapital) * 100
      : 0

  const header = (
    <div className="page-header">
      <h2>{t('portfolio.title')}</h2>
      <p className="subtitle">{t('portfolio.subtitle')}</p>
    </div>
  )

  if (loading) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="error" style={{ padding: 40 }}>{error}</div>
          <button className="btn" style={{ marginTop: 12 }} onClick={load}>
            {t('common.retry')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      {header}

      <div className="grid-4">
        <div className="card">
          <div className="stat-value">{money(summary?.net_worth ?? 0)}</div>
          <div className="stat-change">{t('portfolio.totalValue')}</div>
        </div>
        <div className="card">
          <div className="stat-value">{money(summary?.cash ?? 0)}</div>
          <div className="stat-change">{t('portfolio.availableCash')}</div>
        </div>
        <div className="card">
          <div className="stat-value">{rows.length}</div>
          <div className="stat-change">{t('portfolio.positions')}</div>
        </div>
        <div className="card">
          {/* 涨红跌绿（A 股惯例） */}
          <div className={`stat-value ${totalReturnPct >= 0 ? 'cn-up' : 'cn-down'}`}>
            {totalReturnPct >= 0 ? '+' : ''}{pct(totalReturnPct)}
          </div>
          <div className="stat-change">
            {t('portfolio.totalReturn')}
            <span style={{ color: 'var(--text-secondary)' }}>
              {' '}· {t('portfolio.returnNote')}
            </span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('portfolio.positions')}</span>
          <button className="btn btn-sm" onClick={load}>{t('common.refresh')}</button>
        </div>
        {rows.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>💼</div>
            <div style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
              {t('portfolio.noPositions')}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 16 }}>
              {t('portfolio.noPositionsHint')}
            </div>
            <Link className="btn btn-primary" to="/orders">
              {t('portfolio.goToOrders')}
            </Link>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('equities.ticker')}</th>
                <th>{t('portfolio.quantity')}</th>
                <th>{t('portfolio.avgPrice')}</th>
                <th>
                  {t('portfolio.currentPrice')}
                  <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>
                    {' '}· {t('portfolio.livePrice')}
                  </span>
                </th>
                <th>{t('portfolio.marketValue')}</th>
                <th>{t('portfolio.pnl')}</th>
                <th>{t('portfolio.pnlPercent')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ position, displayPrice, marketValue, unrealizedPnl, pnlPercent }) => (
                <tr key={position.ticker}>
                  <td><strong>{position.ticker}</strong></td>
                  <td>{position.quantity}</td>
                  <td>{money(position.avg_price)}</td>
                  <td>{money(displayPrice)}</td>
                  <td>{money(marketValue)}</td>
                  <td className={unrealizedPnl >= 0 ? 'cn-up' : 'cn-down'}>
                    {unrealizedPnl >= 0 ? '+' : ''}{money(unrealizedPnl)}
                  </td>
                  <td className={pnlPercent >= 0 ? 'cn-up' : 'cn-down'}>
                    {pnlPercent >= 0 ? '+' : ''}{pct(pnlPercent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <span className="card-title">{t('portfolio.allocation')}</span>
        </div>
        <PieChartComponent
          data={allocation}
          title={t('portfolio.allocation')}
          height={260}
        />
      </div>
    </div>
  )
}
