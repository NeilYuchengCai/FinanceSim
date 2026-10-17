import { useEffect, useState, useCallback } from 'react'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import './GlobalClock.css'

// 英文星期几 -> i18n 键（中英文由字典提供）
const WEEKDAY_KEYS: Record<string, string> = {
  Monday: 'simulation.weekdayMonday',
  Tuesday: 'simulation.weekdayTuesday',
  Wednesday: 'simulation.weekdayWednesday',
  Thursday: 'simulation.weekdayThursday',
  Friday: 'simulation.weekdayFriday',
  Saturday: 'simulation.weekdaySaturday',
  Sunday: 'simulation.weekdaySunday',
}

// 市场状态 -> i18n 键（紧凑时钟用短标签）
const MARKET_STATUS_KEYS: Record<string, string> = {
  OPEN: 'simulation.statusOpen',
  WEEKEND: 'simulation.statusWeekend',
  CLOSED: 'simulation.statusClosed',
  HOLIDAY: 'simulation.statusClosed',
}

function formatSimTime(iso?: string): string {
  if (!iso) return '--:--:--'
  return iso.replace('T', ' ').slice(11, 19)
}

function getWeekdayLabel(weekday?: string): string {
  const key = weekday ? WEEKDAY_KEYS[weekday] : undefined
  return key ? t(key) : (weekday ?? '')
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
  const statusText = t(MARKET_STATUS_KEYS[marketStatus] ?? 'simulation.statusClosed')

  return (
    <div className="global-clock" title={`${t('simulation.title')} | Day ${day}`}>
      <div className="clock-top">
        <span className="clock-date">
          {date} {getWeekdayLabel(weekday)}
        </span>
        <span className={`clock-dot ${statusClass}`} title={`${marketStatus} · ${statusText}`} />
      </div>
      <div className="clock-time">{time}</div>
      <div className="clock-bottom">
        <span className="clock-chip">
          {isPaused ? `⏸ ${t('simulation.paused')}` : `▶ ${speed}`}
        </span>
        <span className="clock-chip">Day {day}</span>
        <span className={`clock-status ${statusClass}`}>{statusText}</span>
      </div>
    </div>
  )
}
