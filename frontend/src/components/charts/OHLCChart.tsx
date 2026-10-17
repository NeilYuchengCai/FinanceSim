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

    // lightweight-charts 只接受 'YYYY-MM-DD'（交易日）或 UNIX 时间戳，
    // 后端 /price-history 返回的是 'YYYY-MM-DDTHH:MM:SS'（含 T），会直接抛错导致整页崩溃。
    // 这里统一规整为日期串、过滤非法/缺失值、去重并按时间升序，确保图表稳定渲染。
    const normalized = data
      .filter(
        (d) =>
          d &&
          typeof d.time === 'string' &&
          /^\d{4}-\d{2}-\d{2}/.test(d.time) &&
          [d.open, d.high, d.low, d.close].every((v) => Number.isFinite(v)),
      )
      .map((d) => ({ ...d, time: d.time.slice(0, 10) }))
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
    const seen = new Set<string>()
    const deduped = normalized.filter((d) => {
      if (seen.has(d.time)) return false
      seen.add(d.time)
      return true
    })

    try {
      candlestick.setData(deduped)
      chart.timeScale().fitContent()
    } catch (e) {
      // 任何数据形态异常都不应拖垮整个资产详情页
      console.error('[OHLCChart] setData failed', e, deduped)
    }

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
