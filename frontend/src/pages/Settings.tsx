import { t } from '../i18n'

export default function Settings() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('settings.title')}</h2>
        <p className="subtitle">{t('settings.subtitle', '配置模拟选项')}</p>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('settings.general', '通用设置')}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label>{t('settings.theme')}</label>
            <select className="input-field">
              <option value="dark">{t('settings.dark')}</option>
              <option value="light">{t('settings.light')}</option>
            </select>
          </div>
          <div>
            <label>{t('settings.language')}</label>
            <select className="input-field">
              <option value="zh-CN">{t('settings.chinese')}</option>
              <option value="en">English</option>
            </select>
          </div>
          <div>
            <label>{t('settings.currencyDisplay', '货币显示')}</label>
            <select className="input-field">
              <option>USD ($)</option>
              <option>EUR (€)</option>
              <option>CNY (¥)</option>
              <option>CHF (Fr)</option>
            </select>
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
            <select className="input-field">
              <option>1x</option>
              <option>10x</option>
              <option>100x</option>
              <option>1000x</option>
            </select>
          </div>
          <div>
            <label>{t('settings.dataSource', '数据源')}</label>
            <select className="input-field">
              <option>{t('settings.fallback', '内置数据')}</option>
              <option>Alpha Vantage</option>
              <option>FRED</option>
              <option>Frankfurter</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
