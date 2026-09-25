import { t } from '../i18n'

export default function Challenges() {
  return (
    <div>
      <div className="page-header">
        <h2>🏆 {t('challenges.title')}</h2>
        <p className="subtitle">{t('challenges.subtitle', '完成指定投资目标，测试交易技能')}</p>
      </div>

      <div className="grid-3">
        {[
          { key: 'beginner', icon: '🌱', color: '#22c55e' },
          { key: 'intermediate', icon: '🔥', color: '#f59e0b' },
          { key: 'expert', icon: '💎', color: '#8b5cf6' },
        ].map(item => (
          <div key={item.key} className="card" style={{ cursor: 'pointer', textAlign: 'center', padding: 32 }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>{item.icon}</div>
            <h3 style={{ margin: '0 0 8px', color: item.color }}>{t(`challenges.${item.key}`)}</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('challenges.description', '完成挑战目标，证明你的投资实力')}</p>
            <button className="btn btn-primary" style={{ marginTop: 16, width: '100%' }}>{t('challenges.start', '开始挑战')}</button>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('challenges.yourProgress', '您的进度')}</span>
        </div>
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
          {t('challenges.noChallenges', '暂无进行中的挑战，选择一个挑战开始吧！')}
        </div>
      </div>
    </div>
  )
}
