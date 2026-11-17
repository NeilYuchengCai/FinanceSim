import { useEffect, useState } from 'react'
import {
  t,
  useLanguage,
  formatCurrency,
  CURRENCIES,
} from '../i18n'
import type { CurrencyCode, LanguageCode } from '../i18n'
import { useTheme } from '../hooks/useTheme'
import type { ThemeMode } from '../hooks/useTheme'
import { useSettings, updateSettings, SPEED_OPTIONS, DATA_SOURCE_OPTIONS } from '../hooks/useSettings'
import type { SpeedValue, DataSourceValue } from '../hooks/useSettings'

const DATA_SOURCE_LABELS: Record<string, string> = {
  fallback: '内置数据',
  'alpha-vantage': 'Alpha Vantage / CNBC',
  fred: 'FRED',
  frankfurter: 'Frankfurter',
}

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage } = useLanguage()
  const settings = useSettings()
  const persist = (patch: Parameters<typeof updateSettings>[0]) => updateSettings(patch)
  const [avail, setAvail] = useState<Record<string, any>>({})

  // 挂载时拉取后端数据源可用性；并把本地已选项重新应用到后端，
  // 使后端在重启后也与 UI 选择保持一致（OFFLINE-FIRST：拿不到后端就静默用内置数据）。
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/v1/settings/datasource')
        const d = await r.json()
        setAvail(d.available || {})
        await fetch('/api/v1/settings/datasource', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: settings.dataSource }),
        })
      } catch {
        /* 后端不可达时静默，仍可用内置数据 */
      }
    })()
  }, [])

  const applyDataSource = (v: DataSourceValue) => {
    persist({ dataSource: v })
    fetch('/api/v1/settings/datasource', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: v }),
    }).catch(() => {})
  }

  return (
    <div>
      <div className="page-header">
        <h2>{t('settings.title')}</h2>
        <p className="subtitle">{t('settings.subtitle')}</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('settings.general')}</span>
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
            <label>{t('settings.currencyDisplay')}</label>
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
              {t('settings.preview')}: {formatCurrency(1234.5, settings.currency, language)}
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('settings.simulation')}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label>{t('settings.defaultSpeed')}</label>
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
            <label>{t('settings.dataSource')}</label>
            <select
              className="input-field"
              value={settings.dataSource}
              onChange={(e) => applyDataSource(e.target.value as DataSourceValue)}
            >
              {DATA_SOURCE_OPTIONS.map(source => (
                <option key={source} value={source}>
                  {source === 'fallback'
                    ? t('settings.fallback')
                    : DATA_SOURCE_LABELS[source]}
                </option>
              ))}
            </select>
            <p className="subtitle" style={{ marginTop: 6 }}>
              {settings.dataSource === 'fallback'
                ? t('settings.dataSourceHintFallback')
                : t('settings.dataSourceHintLive')}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
