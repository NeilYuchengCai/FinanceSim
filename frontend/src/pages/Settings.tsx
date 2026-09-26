import { useEffect, useState } from 'react'
import {
  t,
  useLanguage,
  formatCurrency,
  CURRENCIES,
  isCurrencyCode,
} from '../i18n'
import type { CurrencyCode, LanguageCode } from '../i18n'
import { useTheme } from '../hooks/useTheme'
import type { ThemeMode } from '../hooks/useTheme'

const SETTINGS_STORAGE_KEY = 'financesim-settings'

// Aligned with backend: /api/v1/simulation/{world_id}/speed?speed=X1
const SPEED_OPTIONS = ['X1', 'X10', 'X100', 'X1000'] as const
const DATA_SOURCE_OPTIONS = ['fallback', 'alpha-vantage', 'fred', 'frankfurter'] as const

const DATA_SOURCE_LABELS: Record<string, string> = {
  fallback: 'Built-in Data',
  'alpha-vantage': 'Alpha Vantage',
  fred: 'FRED',
  frankfurter: 'Frankfurter',
}

type SpeedValue = typeof SPEED_OPTIONS[number]
type DataSourceValue = typeof DATA_SOURCE_OPTIONS[number]

interface AppSettings {
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
    const parsed = JSON.parse(raw) || {}
    return {
      currency: isCurrencyCode(parsed.currency) ? parsed.currency : DEFAULT_SETTINGS.currency,
      defaultSpeed: SPEED_OPTIONS.includes(parsed.defaultSpeed)
        ? parsed.defaultSpeed
        : DEFAULT_SETTINGS.defaultSpeed,
      dataSource: DATA_SOURCE_OPTIONS.includes(parsed.dataSource)
        ? parsed.dataSource
        : DEFAULT_SETTINGS.dataSource,
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage } = useLanguage()
  const [settings, setSettings] = useState<AppSettings>(loadSettings)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!saved) return
    const timer = setTimeout(() => setSaved(false), 2500)
    return () => clearTimeout(timer)
  }, [saved])

  const persist = (patch: Partial<AppSettings>) => {
    const next = { ...settings, ...patch }
    setSettings(next)
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next))
    } catch {
      /* storage unavailable - keep in-memory state */
    }
    setSaved(true)
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('settings.title')}</h2>
        <p className="subtitle">{t('settings.subtitle', '配置模拟选项')}</p>
      </div>

      {saved && (
        <div className="card" style={{ borderColor: 'var(--accent-color, #4ade80)' }}>
          <div className="card-header">
            <span className="card-title">
              ✅ {t('common.success')} — {t('settings.saved', 'Settings saved')}
            </span>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('settings.general', '通用设置')}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label>{t('settings.theme')}</label>
            <select
              className="input-field"
              value={theme}
              onChange={(e) => setTheme(e.target.value as ThemeMode)}
            >
              <option value="dark">{t('settings.dark')}</option>
              <option value="light">{t('settings.light')}</option>
            </select>
          </div>
          <div>
            <label>{t('settings.language')}</label>
            <select
              className="input-field"
              value={language}
              onChange={(e) => setLanguage(e.target.value as LanguageCode)}
            >
              <option value="zh">{t('settings.chinese')}</option>
              <option value="en">English</option>
            </select>
          </div>
          <div>
            <label>{t('settings.currencyDisplay', '货币显示')}</label>
            <select
              className="input-field"
              value={settings.currency}
              onChange={(e) => persist({ currency: e.target.value as CurrencyCode })}
            >
              {CURRENCIES.map(c => (
                <option key={c.code} value={c.code}>{c.code} ({c.symbol})</option>
              ))}
            </select>
            <p className="subtitle" style={{ marginTop: 6 }}>
              {t('settings.preview', '预览')}: {formatCurrency(1234.5, settings.currency, language)}
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('settings.simulation', '模拟设置')}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label>{t('settings.defaultSpeed', '默认速度')}</label>
            <select
              className="input-field"
              value={settings.defaultSpeed}
              onChange={(e) => persist({ defaultSpeed: e.target.value as SpeedValue })}
            >
              {SPEED_OPTIONS.map(speed => (
                <option key={speed} value={speed}>{speed.replace('X', '')}x</option>
              ))}
            </select>
          </div>
          <div>
            <label>{t('settings.dataSource', '数据源')}</label>
            <select
              className="input-field"
              value={settings.dataSource}
              onChange={(e) => persist({ dataSource: e.target.value as DataSourceValue })}
            >
              {DATA_SOURCE_OPTIONS.map(source => (
                <option key={source} value={source}>
                  {source === 'fallback' ? t('settings.fallback', '内置数据') : DATA_SOURCE_LABELS[source]}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
