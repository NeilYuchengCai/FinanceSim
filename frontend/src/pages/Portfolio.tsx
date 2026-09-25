import { t } from '../i18n'

export default function Portfolio() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('portfolio.title')}</h2>
        <p className="subtitle">{t('portfolio.subtitle', '投资组合概览')}</p>
      </div>
      
      <div className="grid-4">
        <div className="card">
          <div className="stat-value">$0.00</div>
          <div className="stat-change">{t('portfolio.totalValue')}</div>
        </div>
        <div className="card">
          <div className="stat-value">$0.00</div>
          <div className="stat-change">{t('portfolio.availableCash')}</div>
        </div>
        <div className="card">
          <div className="stat-value">0</div>
          <div className="stat-change">{t('portfolio.positions')}</div>
        </div>
        <div className="card">
          <div className="stat-value">0.00%</div>
          <div className="stat-change">{t('portfolio.totalReturn')}</div>
        </div>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('portfolio.positions')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('portfolio.quantity', '数量')}</th>
              <th>{t('portfolio.avgPrice', '均价')}</th>
              <th>{t('portfolio.currentPrice', '现价')}</th>
              <th>{t('portfolio.marketValue', '市值')}</th>
              <th>{t('portfolio.pnl', '盈亏')}</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colSpan={6} className="loading">{t('portfolio.noPositions', '暂无持仓')}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
