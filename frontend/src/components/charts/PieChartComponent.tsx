import { useEffect, useRef } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface ChartData {
  name: string
  value: number
  color?: string
}

interface PieChartComponentProps {
  data: ChartData[]
  title: string
  height?: number
}

const COLORS = ['#6366f1', '#ef4444', '#22c55e', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6']

export default function PieChartComponent({
  data,
  height = 200
}: PieChartComponentProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.style.height = `${height}px`
    }
  }, [height])

  if (!data || data.length === 0) {
    return (
      <div ref={containerRef} style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
          labelStyle={{ color: '#fff' }}
        />
        <Legend wrapperStyle={{ color: '#9ca3af' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
