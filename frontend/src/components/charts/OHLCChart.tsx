import { useEffect, useRef } from 'react'
import { createChart, ColorType } from 'lightweight-charts'

interface OHLCData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

interface OHLCChartProps {
  data: OHLCData[]
  height?: number
  symbol?: string
}

export default function OHLCChart({
  data,
  height = 400,
  symbol = ''
}: OHLCChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: '#1f2937' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: '#374151' },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    const candlestick = chart.addCandlestickSeries({
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderUpColor: '#ef4444',
      borderDownColor: '#22c55e',
      wickUpColor: '#ef4444',
      wickDownColor: '#22c55e',
    })

    candlestick.setData(data)
    chart.timeScale().fitContent()

    const handleResize = () => {
      if (containerRef.current && chart) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chart) chart.remove()
    }
  }, [data, height, symbol])

  return (
    <div ref={containerRef} style={{ height, width: '100%' }} />
  )
}
