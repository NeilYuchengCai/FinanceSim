import { useEffect, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

/**
 * 收益率曲线图（Wave 2）
 * 数据契约：GET /api/v1/bonds/yield-curve -> [{ tenor: 年, yield: 小数 }]
 */

export interface YieldCurvePoint {
  tenor: number
  yield: number
}

interface YieldCurveChartProps {
  data: YieldCurvePoint[]
  height?: number
}

const tooltipStyle = {
  background: '#1f2937',
  border: '1px solid #374151',
  borderRadius: '8px',
} as const

export default function YieldCurveChart({ data, height = 260 }: YieldCurveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.style.height = `${height}px`
    }
  }, [height])

  if (!data || data.length === 0) {
    return (
      <div
        ref={containerRef}
        style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}
      >
        No data available
      </div>
    )
  }

  // tenor 保留原始精度展示；yield 换算为百分数
  const chartData = data.map((p) => ({
    tenor: p.tenor,
    yieldPct: Number((p.yield * 100).toFixed(3)),
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 24, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="tenor"
          stroke="#9ca3af"
          fontSize={12}
          tickFormatter={(v: number) => `${v}Y`}
        />
        <YAxis stroke="#9ca3af" fontSize={12} unit="%" />
        <Tooltip
          contentStyle={tooltipStyle}
          labelStyle={{ color: '#fff' }}
          formatter={(value: number) => [`${value}%`, 'Yield']}
          labelFormatter={(label: number) => `Tenor: ${label}Y`}
        />
        <Line
          type="monotone"
          dataKey="yieldPct"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Yield"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
