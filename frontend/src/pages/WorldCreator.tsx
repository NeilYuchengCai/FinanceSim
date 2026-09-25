import { t } from '../i18n'

export default function WorldCreator() {
  return (
    <div>
      <div className="page-header">
        <h2>🌐 {t('world.title')}</h2>
        <p className="subtitle">{t('world.subtitle', '创建、管理和分支模拟世界')}</p>
      </div>

      <div className="grid-3">
        {[
          { mode: 'demo', icon: '🎮', label: t('world.demo', '演示模式') },
          { mode: 'sandbox', icon: '🔬', label: t('world.sandbox', '沙盒模式') },
          { mode: 'competitive', icon: '🏆', label: t('world.competitive', '竞技模式') },
        ].map(item => (
          <div key={item.mode} className="card" style={{ textAlign: 'center', padding: 32, cursor: 'pointer' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>{item.icon}</div>
            <h3 style={{ margin: '0 0 8px' }}>{item.label}</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('world.selectWorld', '选择一个模式开始')}</p>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('world.worlds', '世界列表')}</span>
          <span className="tag tag-blue">0</span>
        </div>
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
          {t('world.noWorlds', '暂无世界，点击创建按钮开始')}
        </div>
      </div>
    </div>
  )
}
