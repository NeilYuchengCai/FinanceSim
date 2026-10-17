import { useEffect, useRef, useState, useCallback } from 'react'
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

const POLL_MS = 1000

function pad(n: number): string {
  return n < 10 ? '0' + n : '' + n
}

function fmtTime(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function fmtDate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// 后端返回的是 naive ISO 串（无时区），直接 Date.parse 会被套用浏览器本地时区而偏移。
// 这里按字符串分量构造本地 Date，保留原始墙钟时间，避免显示错位。
function parseSim(iso?: string): number | null {
  if (!iso) return null
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/.exec(iso)
  if (!m) return null
  return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]).getTime()
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

  // 平滑动画用的引用：目标时间 / 上一目标 / 上次更新时刻(ms)
  const targetRef = useRef<number | null>(null)
  const prevTargetRef = useRef<number | null>(null)
  const lastUpdateRef = useRef<number>(0)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/simulation/${worldId}/status`)
      if (res.ok) {
        const data = await res.json()
        const tMs = parseSim(data.current_time)
        if (tMs !== null) {
          if (targetRef.current === null) {
            // 首次：直接锚定，避免从 epoch 一路飞过
            prevTargetRef.current = tMs
            targetRef.current = tMs
          } else {
            prevTargetRef.current = targetRef.current
            targetRef.current = tMs
          }
          lastUpdateRef.current = performance.now()
        }
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

  // 平滑动画：在两次轮询之间，让显示时间从 prevTarget 线性推进到 target，
  // 时钟因此"流动"而不是每秒整点跳变。
  useEffect(() => {
    let raf = 0
    const tick = () => {
      const target = targetRef.current
      const prev = prevTargetRef.current
      if (target !== null && prev !== null) {
        const elapsed = performance.now() - lastUpdateRef.current
        const frac = Math.min(Math.max(elapsed / POLL_MS, 0), 1)
        const shown = prev + (target - prev) * frac
        const d = new Date(shown)
        setTime(fmtTime(d))
        setDate(fmtDate(d))
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, POLL_MS)
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
