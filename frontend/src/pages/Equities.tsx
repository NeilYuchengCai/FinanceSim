import { t } from '../i18n'

export default function Equities() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('equities.title')}</h2>
        <p className="subtitle">{t('equities.subtitle')}</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('equities.marketSummary', '市场摘要')}</span>
          <span className="tag tag-blue">SIMULATION</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('equities.change')}</th>
              <th>{t('equities.volume')}</th>
              <th>{t('equities.marketCap', '市值')}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6} className="loading">{t('common.loading')}</td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div className="grid-3" style={{marginTop: 20}}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('equities.topGainers', '涨幅榜')}</span>
          </div>
          <div style={{padding: 20, textAlign: 'center', color: 'var(--text-secondary)'}}>
            {t('common.loading')}
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('equities.topLosers', '跌幅榜')}</span>
          </div>
          <div style={{padding: 20, textAlign: 'center', color: 'var(--text-secondary)'}}>
            {t('common.loading')}
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('equities.mostActive', '活跃榜')}</span>
          </div>
          <div style={{padding: 20, textAlign: 'center', color: 'var(--text-secondary)'}}>
            {t('common.loading')}
          </div>
        </div>
      </div>
    </div>
  )
}
