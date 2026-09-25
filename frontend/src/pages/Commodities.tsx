import { t } from '../i18n'

const CATEGORY_NAMES: Record<string, string> = {
  ALL: t('commodities.all', '全部'),
  ENERGY: t('commodities.energy'),
  METAL: t('commodities.metals'),
  AGRICULTURE: t('commodities.agriculture'),
  PRECIOUS_METAL: t('commodities.precious'),
}

export default function Commodities() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('commodities.title')}</h2>
        <p className="subtitle">{t('commodities.subtitle', '全球商品市场')} · <span className="data-source simulated">{t('commodities.simulated', '模拟数据')}</span></p>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card-header">
          <span className="card-title">{t('commodities.categories', '分类')}</span>
        </div>
        <div style={{display: 'flex', gap: 8, flexWrap: 'wrap'}}>
          {Object.entries(CATEGORY_NAMES).map(([cat, name]) => (
            <button key={cat} style={{
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
            }}>
              {name}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('commodities.allCommodities', '所有商品')}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('commodities.category', '分类')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('commodities.volatility', '波动率')}</th>
              <th>{t('commodities.supplyDemand', '供需')}</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colSpan={6} className="loading">{t('common.loading')}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
