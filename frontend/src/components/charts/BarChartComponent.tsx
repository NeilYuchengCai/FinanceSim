import { useEffect, useRef } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface ChartData {
  name: string
  value: number
  fill?: string
}

interface BarChartComponentProps {
  data: ChartData[]
  title: string
  height?: number
}

export default function BarChartComponent({
  data,
  title,
  height = 200
}: BarChartComponentProps) {
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
      <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
        <YAxis stroke="#9ca3af" fontSize={12} />
        <Tooltip
          contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
          labelStyle={{ color: '#fff' }}
        />
        <Legend wrapperStyle={{ color: '#9ca3af' }} />
        <Bar
          dataKey="value"
          fill="#6366f1"
          name={title}
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
