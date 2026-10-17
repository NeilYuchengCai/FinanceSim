/**
 * 全局设置存储（货币/速度/数据源）。
 *
 * 原先 currency 只是 Settings 页的局部 useState，切换后其它页面完全不知道，
 * 所以"货币切换"看起来像没生效。这里抽成 module-level store + useSyncExternalStore，
 * 任何页面订阅后都能随展示货币变化重新渲染；formatMoney 也直接读全局展示货币。
 */
import { useSyncExternalStore } from 'react'
import { isCurrencyCode, type CurrencyCode } from '../i18n'

const SETTINGS_STORAGE_KEY = 'financesim-settings'

export const SPEED_OPTIONS = ['X1', 'X10', 'X100', 'X1000'] as const
export type SpeedValue = (typeof SPEED_OPTIONS)[number]

export const DATA_SOURCE_OPTIONS = ['fallback', 'alpha-vantage', 'fred', 'frankfurter'] as const
export type DataSourceValue = (typeof DATA_SOURCE_OPTIONS)[number]

export interface AppSettings {
  currency: CurrencyCode
  defaultSpeed: SpeedValue
  dataSource: DataSourceValue
}

const DEFAULT_SETTINGS: AppSettings = {
  currency: 'USD',
  defaultSpeed: 'X10',
  dataSource: 'fallback',
}

function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (!raw) return DEFAULT_SETTINGS
    const p = JSON.parse(raw) || {}
    return {
      currency: isCurrencyCode(p.currency) ? p.currency : DEFAULT_SETTINGS.currency,
      defaultSpeed: SPEED_OPTIONS.includes(p.defaultSpeed) ? p.defaultSpeed : DEFAULT_SETTINGS.defaultSpeed,
      dataSource: DATA_SOURCE_OPTIONS.includes(p.dataSource) ? p.dataSource : DEFAULT_SETTINGS.dataSource,
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

let settings: AppSettings = loadSettings()
const listeners = new Set<() => void>()

function emit() {
  for (const l of listeners) l()
}

export function updateSettings(patch: Partial<AppSettings>): void {
  settings = { ...settings, ...patch }
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  } catch {
    /* storage unavailable - keep in-memory state */
  }
  emit()
}

export function getSettings(): AppSettings {
  return settings
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb)
  return () => {
    listeners.delete(cb)
  }
}

export function useSettings(): AppSettings {
  return useSyncExternalStore(subscribe, getSettings, getSettings)
}
