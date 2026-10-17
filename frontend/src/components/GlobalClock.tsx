import { useEffect, useState, useCallback } from 'react'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import './GlobalClock.css'

const STORAGE_KEY = 'financesim-world-state'

interface WorldState {
  current_day: number
  current_time: string
  speed: string
  is_paused: boolean
}

// 星期几的中英文映射
const WEEKDAY_EN_ZH: Record<string, string> = {
  Monday: '周一',
  Tuesday: '周二',
  Wednesday: '周三',
  Thursday: '周四',
  Friday: '周五',
  Saturday: '周六',
  Sunday: '周日',
}

function formatSimTime(iso?: string): string {
  if (!iso) return '--:--:--'
  return iso.replace('T', ' ').slice(11, 19)
}

function getWeekdayCN(weekday?: string): string {
  return weekday ? (WEEKDAY_EN_ZH[weekday] ?? weekday) : ''
}

export default function GlobalClock() {
  const { worldId } = useCurrentWorld()
  const [time, setTime] = useState<string>('--:--:--')
  const [date, setDate] = useState<string>('')
  const [weekday, setWeekday] = useState<string>('')
  const [marketStatus, setMarketStatus] = useState<'OPEN' | 'CLOSED' | 'WEEKEND' | 'HOLIDAY'>('CLOSED')
  const [speed, setSpeed] = useState<string>('X1')
  const [day, setDay] = useState<number>(0)
  const [isPaused, setIsPaused] = useState<boolean>(true)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/simulation/${worldId}/status`)
      if (res.ok) {
        const data = await res.json()
        setTime(formatSimTime(data.current_time))
        setDate(data.current_time?.slice(0, 10) ?? '')
        setWeekday(data.weekday ?? '')
        setMarketStatus(data.market_status ?? 'CLOSED')
        setSpeed(data.speed ?? 'X1')
        setDay(data.current_day ?? 0)
        setIsPaused(data.is_paused ?? true)
      }
    } catch {
      // 静默失败，保持当前显示
    }
  }, [worldId])

  useEffect(() => {
    // 初始加载
    fetchStatus()

    // 每1秒刷新一次（与模拟tick同步）
    const interval = setInterval(fetchStatus, 1000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const statusClass = marketStatus === 'OPEN' ? 'open' : marketStatus === 'WEEKEND' ? 'weekend' : 'closed'
  const statusText = marketStatus === 'OPEN' ? '开市' : marketStatus === 'WEEKEND' ? '周末' : '休市'

  return (
    <div className="global-clock" title={`${t('simulation.title')} | Day ${day}`}>
      <div className="clock-top">
        <span className="clock-date">
          {date} {getWeekdayCN(weekday)}
        </span>
        <span className={`clock-dot ${statusClass}`} title={`${marketStatus} · ${statusText}`} />
      </div>
      <div className="clock-time">{time}</div>
      <div className="clock-bottom">
        <span className="clock-chip">
          {isPaused ? '⏸ 暂停' : `▶ ${speed}`}
        </span>
        <span className="clock-chip">Day {day}</span>
        <span className={`clock-status ${statusClass}`}>{statusText}</span>
      </div>
    </div>
  )
}
