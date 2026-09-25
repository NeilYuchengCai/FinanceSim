import { t } from '../i18n'

export default function FX() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('fx.title')}</h2>
        <p className="subtitle">{t('fx.subtitle', '货币对实时汇率')}</p>
      </div>

      <div className="grid-3">
        {['USD/CNY', 'EUR/USD', 'GBP/USD', 'USD/CHF', 'USD/JPY', 'AUD/USD'].map(pair => (
          <div key={pair} className="card">
            <div className="card-header">
              <span className="card-title">{pair}</span>
              <span className="badge badge-dot green"></span>
            </div>
            <div className="stat-value">--</div>
            <div className="stat-change positive">+0.000%</div>
            <div className="stat-change">Spread: -- pips | Vol: --%</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('fx.crossRates', '交叉汇率')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('fx.base', '基准')}</th>
              <th>{t('fx.quote', '报价')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('fx.change24h', '24h涨跌')}</th>
              <th>{t('fx.spread', '点差')}</th>
              <th>{t('fx.high24h', '24h最高')}</th>
              <th>{t('fx.low24h', '24h最低')}</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colSpan={8} className="loading">{t('common.loading')}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
