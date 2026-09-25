import { t } from '../i18n'

export default function Bonds() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('bonds.title')}</h2>
        <p className="subtitle">{t('bonds.subtitle', '国债和企业债')}</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('bonds.yieldCurve')}</span>
        </div>
        <div className="chart-container" style={{height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <span className="loading">{t('common.loading')}</span>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('bonds.bondList', '债券列表')}</span>
          <select className="input-field" style={{ width: 'auto' }}>
            <option value="ALL">{t('bonds.all', '全部')}</option>
            <option value="UST">{t('bonds.treasury', '国债')}</option>
            <option value="IG">{t('bonds.investmentGrade', '投资级')}</option>
            <option value="HY">{t('bonds.highYield', '高收益')}</option>
          </select>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>{t('equities.ticker')}</th>
              <th>{t('equities.name')}</th>
              <th>{t('bonds.type', '类型')}</th>
              <th>{t('bonds.rating')}</th>
              <th>{t('bonds.coupon')}</th>
              <th>{t('equities.price')}</th>
              <th>{t('bonds.ytm', '到期收益率')}</th>
              <th>{t('bonds.duration')}</th>
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
