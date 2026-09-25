import { useState } from 'react'
import { t } from '../i18n'

export default function Simulation() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [currentDay] = useState(0)

  return (
    <div>
      <div className="page-header">
        <h2>{t('simulation.title')}</h2>
        <p className="subtitle">{t('simulation.subtitle', '控制模拟时钟')}</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('simulation.controls', '模拟控制')}</span>
          <span className="badge badge-dot green"></span>
        </div>

        <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          <div>
            <div className="stat-value">{t('overview.day', '第')} {currentDay} {t('overview.day', '天')}</div>
            <div className="stat-change">{t('simulation.currentDay', '当前日期')}</div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-primary" onClick={() => setIsPlaying(!isPlaying)}>
              {isPlaying ? t('simulation.pause', '暂停') : t('simulation.play', '播放')}
            </button>
            <button className="btn btn-secondary">{t('simulation.step', '执行一步')}</button>
          </div>

          <div>
            <label>{t('simulation.speed', '速度')}: </label>
            <select className="input-field" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
              <option value={1}>1x</option>
              <option value={10}>10x</option>
              <option value={100}>100x</option>
              <option value={1000}>1000x</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('overview.marketRegime', '市场状态')}</span>
          </div>
          <div className="stat-value">CALM</div>
          <div className="stat-change">{t('simulation.currentState', '当前市场状态')}</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('simulation.todayEvents', '今日事件')}</span>
          </div>
          <div className="stat-value">0</div>
          <div className="stat-change">{t('simulation.scheduledEvents', '计划事件')}</div>
        </div>
      </div>
    </div>
  )
}
