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
  fallback: 'Built-in Data',
  'alpha-vantage': 'Alpha Vantage',
  fred: 'FRED',
  frankfurter: 'Frankfurter',
}

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage } = useLanguage()
  const settings = useSettings()
  const persist = (patch: Parameters<typeof updateSettings>[0]) => updateSettings(patch)

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
              onChange={(e) => persist({ dataSource: e.target.value as DataSourceValue })}
            >
              {DATA_SOURCE_OPTIONS.map(source => {
                // 后端目前仅产出模拟数据（各引擎 data_source = "SIMULATED"），
                // 外部数据源尚未接入：置灰标注，避免用户误选后以为生效。
                const integrated = source === 'fallback'
                return (
                  <option key={source} value={source} disabled={!integrated}>
                    {source === 'fallback'
                      ? t('settings.fallback')
                      : `${DATA_SOURCE_LABELS[source]} ${t('settings.dataSourceNotIntegrated')}`}
                  </option>
                )
              })}
            </select>
            <p className="subtitle" style={{ marginTop: 6 }}>
              {t('settings.dataSourceHint')}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
