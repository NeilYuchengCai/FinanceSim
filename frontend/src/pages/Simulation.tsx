import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'

// 后端 SimulationSpeed 枚举名，/speed 只接受这四个大写值
const SPEED_OPTIONS = ['X1', 'X10', 'X100', 'X1000'] as const
type Speed = typeof SPEED_OPTIONS[number]

// 与设置页共享的持久化 key（Settings.tsx 负责写入，本页面只读不回写，避免两页互相打架）
const SETTINGS_STORAGE_KEY = 'financesim-settings'

// 读取设置页的「默认速度」；key 不存在 / JSON 损坏 / 字段缺失 / 值非法，一律退化为 X1
function loadDefaultSpeed(): Speed {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (!raw) return 'X1'
    const parsed = JSON.parse(raw) || {}
    const value = parsed.defaultSpeed
    return (SPEED_OPTIONS as readonly string[]).includes(value) ? (value as Speed) : 'X1'
  } catch {
    return 'X1'
  }
}

// 倍率越高，tick 越密，避免高速下天数跳变过慢
const TICK_INTERVAL: Record<Speed, number> = {
  X1: 1000,
  X10: 1000,
  X100: 500,
  X1000: 300,
}

interface SimStatus {
  current_day: number
  current_time: string
  speed: string
  is_paused: boolean
  // 交易日历字段（后端 SimulationClock.get_status() 提供）
  weekday?: string          // 英文星期几，如 'Monday'
  is_trading_day?: boolean  // 是否交易日
  market_status?: string    // OPEN / CLOSED / WEEKEND / HOLIDAY
  next_trading_day?: string // YYYY-MM-DD
  holiday_name?: string     // 节假日名称，非节假日为空串
}

// 市场状态 -> 徽章配色（index.css 里只有 tag-green / tag-red / tag-blue / tag-yellow）
const MARKET_TAG_CLASS: Record<string, string> = {
  OPEN: 'tag-green',
  CLOSED: 'tag-blue',
  WEEKEND: 'tag-yellow',
  HOLIDAY: 'tag-red',
}

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

// 市场状态 -> i18n 键
const MARKET_LABEL_KEYS: Record<string, string> = {
  OPEN: 'simulation.marketOpen',
  CLOSED: 'simulation.marketClosed',
  WEEKEND: 'simulation.marketWeekend',
  HOLIDAY: 'simulation.marketHoliday',
}

const marketTagClass = (s?: string) => MARKET_TAG_CLASS[s ?? ''] ?? 'tag-blue'
const marketLabel = (s?: string) => {
  const key = MARKET_LABEL_KEYS[s ?? '']
  return key ? t(key) : ''
}
const weekdayLabel = (w?: string) => {
  const key = w ? WEEKDAY_KEYS[w] : undefined
  return key ? t(key) : ''
}

interface EconomyState {
  cycle_phase: string
  cycle_position: number
  gdp_growth: number
  inflation: number
  unemployment: number
  interest_rate: number
}

interface WorldEvent {
  id: string
  type: string
  severity: number
  title: string
  created_at: string
}

const pct = (v: number) => `${(v * 100).toFixed(2)}%`

// 模拟时钟返回的是 ISO 串，直接切片展示，不使用浏览器 now()
function formatSimTime(iso?: string) {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 19)
}

export default function Simulation() {
  const { worldId } = useCurrentWorld()
  const [status, setStatus] = useState<SimStatus | null>(null)
  const [speed, setSpeed] = useState<Speed>(() => loadDefaultSpeed())
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [economy, setEconomy] = useState<EconomyState | null>(null)
  const [economyError, setEconomyError] = useState<string | null>(null)
  const [events, setEvents] = useState<WorldEvent[]>([])
  const [eventsError, setEventsError] = useState<string | null>(null)

  const timerRef = useRef<number | null>(null)

  const refreshStatus = useCallback(async () => {
    const res = await axios.get(`/api/v1/simulation/${worldId}/status`)
    setStatus(res.data)
    return res.data as SimStatus
  }, [worldId])

  const loadEconomy = useCallback(async () => {
    try {
      const res = await axios.get('/api/v1/economy/state')
      setEconomy(res.data)
      setEconomyError(null)
    } catch {
      setEconomyError(t('common.dataError'))
    }
  }, [])

  const loadEvents = useCallback(async () => {
    try {
      const res = await axios.get('/api/v1/events/list', {
        params: { world_id: worldId, limit: 100 },
      })
      setEvents(Array.isArray(res.data) ? res.data : [])
      setEventsError(null)
    } catch {
      setEventsError(t('common.dataError'))
    }
  }, [worldId])

  // 设置页的「默认速度」优先：与后端当前速度不一致时，初始化时同步一次到后端
  const applyDefaultSpeed = useCallback(async (backendSpeed?: string) => {
    const preferred = loadDefaultSpeed()
    if (backendSpeed === preferred) {
      setSpeed(preferred)
      return
    }
    try {
      await axios.post(`/api/v1/simulation/${worldId}/speed`, null, {
        params: { speed: preferred },
      })
      setSpeed(preferred)
    } catch {
      // 同步失败不打断整页：后端速度合法就用后端值，否则保留设置页的值
      if (typeof backendSpeed === 'string' && (SPEED_OPTIONS as readonly string[]).includes(backendSpeed)) {
        setSpeed(backendSpeed as Speed)
      } else {
        setSpeed(preferred)
      }
    }
  }, [worldId])

  const loadAll = useCallback(async () => {
    try {
      const st = await refreshStatus()
      // 进入页面默认暂停：时间绝不应当自作主张地走，必须等用户点“播放”。
      // （若后端世界此前处于运行态，这里也先按暂停呈现，用户手动播放即继续推进。）
      setPlaying(false)
      await applyDefaultSpeed(st?.speed)
      setError(null)
    } catch {
      setError(t('common.dataError'))
    } finally {
      setLoading(false)
    }
    // 宏观与事件独立容错，一处失败不影响整页
    await Promise.all([loadEconomy(), loadEvents()])
  }, [refreshStatus, applyDefaultSpeed, loadEconomy, loadEvents])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // 时钟自己不会走：播放期间必须持续调 /tick 推进模拟时间
  useEffect(() => {
    if (!playing) return
    let cancelled = false

    const run = async () => {
      try {
        await axios.post(`/api/v1/simulation/${worldId}/tick`)
        const res = await axios.get(`/api/v1/simulation/${worldId}/status`)
        if (!cancelled) {
          setStatus(res.data)
          setError(null)
        }
      } catch {
        if (!cancelled) setError(t('common.dataError'))
      }
    }

    timerRef.current = window.setInterval(run, TICK_INTERVAL[speed])
    return () => {
      cancelled = true
      if (timerRef.current !== null) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [playing, speed, worldId])

  const togglePlay = async () => {
    try {
      if (playing) {
        await axios.post(`/api/v1/simulation/${worldId}/pause`)
        setPlaying(false)
      } else {
        await axios.post(`/api/v1/simulation/${worldId}/start`)
        setPlaying(true)
      }
      await refreshStatus()
      setError(null)
    } catch {
      setError(t('simulation.actionFailed'))
    }
  }

  const stepOnce = async () => {
    try {
      await axios.post(`/api/v1/simulation/${worldId}/step`, null, { params: { days: 1 } })
      await refreshStatus()
      await Promise.all([loadEconomy(), loadEvents()])
      setError(null)
    } catch {
      setError(t('simulation.actionFailed'))
    }
  }

  const changeSpeed = async (next: Speed) => {
    setSpeed(next)
    try {
      await axios.post(`/api/v1/simulation/${worldId}/speed`, null, { params: { speed: next } })
      await refreshStatus()
      setError(null)
    } catch {
      setError(t('simulation.actionFailed'))
    }
  }

  const header = (
    <div className="page-header">
      <h2>{t('simulation.title')}</h2>
      <p className="subtitle">{t('simulation.subtitle')}</p>
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

  if (error && !status) {
    return (
      <div>
        {header}
        <div className="card">
          <div className="error" style={{ padding: 40 }}>{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div>
      {header}

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('simulation.controls')}</span>
          <span className={`badge badge-dot ${playing ? 'green' : 'gray'}`}></span>
        </div>

        <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* 模拟时间：来自后端 start_time 推进，精确到秒 */}
          <div>
            <div className="stat-change">{t('simulation.simTime')}</div>
            <div
              className="stat-value"
              style={{ fontFamily: 'monospace', fontSize: '1.5rem', letterSpacing: '0.5px' }}
            >
              {formatSimTime(status?.current_time)}
            </div>
            <div className="stat-change">
              {status?.weekday
                ? `${status.weekday}${weekdayLabel(status.weekday) ? ` · ${weekdayLabel(status.weekday)}` : ''}`
                : '—'}
            </div>
          </div>

          {/* 交易日历状态徽章 */}
          <div>
            <div className="stat-change">{t('simulation.marketStatus')}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span className={`tag ${marketTagClass(status?.market_status)}`}>
                {status?.market_status ?? '—'}
              </span>
              <span className="stat-change">{marketLabel(status?.market_status)}</span>
              {status?.holiday_name ? (
                <span className="tag tag-red">{status.holiday_name}</span>
              ) : null}
            </div>
            <div className="stat-change">
              {t('simulation.nextTradingDay')}: {status?.next_trading_day ?? '—'}
            </div>
          </div>

          <div>
            <div className="stat-value">
              {t('simulation.dayPrefix')} {status?.current_day ?? 0} {t('overview.day')}
            </div>
            <div className="stat-change">
              {status?.is_trading_day === undefined
                ? ''
                : status.is_trading_day
                  ? t('simulation.tradingDay')
                  : t('simulation.nonTradingDay')}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-primary" onClick={togglePlay}>
              {playing ? t('simulation.pause') : t('simulation.play')}
            </button>
            <button className="btn btn-secondary" onClick={stepOnce}>
              {t('simulation.step')}
            </button>
          </div>

          <div>
            <label>{t('simulation.speed')}: </label>
            <select
              className="input-field"
              value={speed}
              onChange={(e) => changeSpeed(e.target.value as Speed)}
            >
              {SPEED_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replace('X', '')}x
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="stat-change">
              {playing ? t('simulation.running') : t('simulation.paused')}
            </div>
          </div>
        </div>

        {error && <div className="error" style={{ padding: 12 }}>{error}</div>}
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.marketRegime')}</span>
            {economy && <span className="tag tag-blue">{economy.cycle_phase}</span>}
          </div>
          {economyError ? (
            <div className="error" style={{ padding: 16 }}>{economyError}</div>
          ) : economy ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('simulation.metric')}</th>
                  <th>{t('markets.price')}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{t('simulation.cyclePhase')}</td>
                  <td>{economy.cycle_phase}</td>
                </tr>
                <tr>
                  <td>{t('simulation.gdpGrowth')}</td>
                  <td className={economy.gdp_growth >= 0 ? 'positive' : 'negative'}>
                    {pct(economy.gdp_growth)}
                  </td>
                </tr>
                <tr>
                  <td>{t('simulation.inflation')}</td>
                  <td>{pct(economy.inflation)}</td>
                </tr>
                <tr>
                  <td>{t('simulation.unemployment')}</td>
                  <td>{pct(economy.unemployment)}</td>
                </tr>
                <tr>
                  <td>{t('simulation.interestRate')}</td>
                  <td>{pct(economy.interest_rate)}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="loading" style={{ padding: 16 }}>{t('common.noData')}</div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('simulation.todayEvents')}</span>
            <span className="tag tag-gray">{events.length}</span>
          </div>
          {eventsError ? (
            <div className="error" style={{ padding: 16 }}>{eventsError}</div>
          ) : events.length === 0 ? (
            <div className="loading" style={{ padding: 16 }}>{t('common.noData')}</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('simulation.eventTime')}</th>
                  <th>{t('simulation.eventTitle')}</th>
                  <th>{t('simulation.eventType')}</th>
                  <th>{t('simulation.severity')}</th>
                </tr>
              </thead>
              <tbody>
                {events.slice(0, 5).map((ev) => (
                  <tr key={ev.id}>
                    <td>{formatSimTime(ev.created_at).slice(0, 16)}</td>
                    <td>{ev.title}</td>
                    <td>{ev.type}</td>
                    <td>{ev.severity.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
