import { t } from '../i18n'

export default function Analytics() {
  return (
    <div>
      <div className="page-header">
        <h2>{t('analytics.title')}</h2>
        <p className="subtitle">{t('analytics.subtitle', '高级财务分析')}</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.returnsAnalysis', '收益分析')}</span>
          </div>
          <div className="chart-container">{t('common.loading')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.riskMetrics', '风险指标')}</span>
          </div>
          <div className="chart-container">{t('common.loading')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.correlationMatrix', '相关性矩阵')}</span>
          </div>
          <div className="chart-container">{t('common.loading')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('analytics.drawdownAnalysis', '回撤分析')}</span>
          </div>
          <div className="chart-container">{t('common.loading')}</div>
        </div>
      </div>
    </div>
  )
}
