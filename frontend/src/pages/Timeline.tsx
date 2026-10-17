import { useState, useEffect } from 'react'
import axios from 'axios'
import OHLCChart from '../components/charts/OHLCChart'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'

interface Event {
  id: string
  type: string
  severity: number
  title: string
  body: string
  affected_assets: string[]
  created_at: string
  duration_days: number
  sentiment_effect?: number
  macro_effect?: Record<string, number>
}

interface PricePoint {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  earnings: t('timeline.earnings', '财报'),
  product_launch: t('timeline.productLaunch', '新品发布'),
  management_change: t('timeline.managementChange', '管理层变动'),
  regulatory: t('timeline.regulatory', '监管事件'),
  ma: t('timeline.ma', '并购'),
  guidance: t('timeline.guidance', '指引'),
  geopolitical: t('timeline.geopolitical', '地缘政治'),
  central_bank: t('timeline.centralBank', '央行决策'),
  inflation_shock: t('timeline.inflationShock', '通胀冲击'),
  employment_shock: t('timeline.employmentShock', '就业冲击'),
  liquidity_crisis: t('timeline.liquidityCrisis', '流动性危机'),
  banking_crisis: t('timeline.bankingCrisis', '银行危机'),
  black_swan: t('timeline.blackSwan', '黑天鹅')
}

export default function TimelinePage() {
  const { worldId } = useCurrentWorld()
  const [events, setEvents] = useState<Event[]>([])
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')

  const fetchEvents = async () => {
    try {
      const res = await axios.get('/api/v1/events/list', { params: { world_id: worldId, limit: 100 } })
      setEvents(res.data || [])
    } catch (e) {
      console.error('Failed to fetch events:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvents()
    const id = setInterval(fetchEvents, 3000)
    return () => clearInterval(id)
  }, [worldId])

  const handleEventClick = async (event: Event) => {
    setSelectedEvent(event)
    if (event.affected_assets.length > 0) {
      try {
        const res = await axios.get('/api/v1/assets/price-history', {
          params: { ticker: event.affected_assets[0], limit: 50 }
        })
        setPriceHistory(res.data || [])
      } catch (e) {
        setPriceHistory([])
      }
    }
  }

  const getSeverityColor = (severity: number) => {
    if (severity >= 0.8) return '#ef4444'
    if (severity >= 0.5) return '#f59e0b'
    return '#6366f1'
  }

  const filteredEvents = filter === 'ALL' ? events : events.filter(e => e.type === filter)

  return (
    <div>
      <div className="page-header">
        <h2>{t('timeline.title')}</h2>
        <p className="subtitle">{t('timeline.subtitle', '市场历史事件记录')}</p>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card-header">
          <span className="card-title">{t('timeline.filters', '筛选')}</span>
        </div>
        <div style={{display: 'flex', gap: 8, flexWrap: 'wrap'}}>
          {['ALL', 'earnings', 'geopolitical', 'central_bank', 'liquidity_crisis', 'black_swan'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: `1px solid ${filter === f ? '#6366f1' : 'var(--border-color)'}`,
                background: filter === f ? '#6366f1' : 'var(--bg-secondary)',
                color: filter === f ? '#fff' : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {f === 'ALL' ? t('timeline.all', '全部') : EVENT_TYPE_LABELS[f] || f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid-2">
        {/* 事件列表 */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">{t('timeline.events', '事件列表')}</span>
            <span className="tag tag-blue">{filteredEvents.length} {t('timeline.items', '条')}</span>
          </div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto'}}>
            {loading ? (
              <div style={{textAlign: 'center', padding: 40, color: 'var(--text-secondary)'}}>{t('common.loading')}</div>
            ) : filteredEvents.length === 0 ? (
              <div style={{textAlign: 'center', padding: 40, color: 'var(--text-secondary)'}}>{t('timeline.noEvents', '暂无事件')}</div>
            ) : (
              filteredEvents.map(event => (
                <div
                  key={event.id}
                  onClick={() => handleEventClick(event)}
                  style={{
                    padding: 12,
                    borderRadius: 6,
                    cursor: 'pointer',
                    borderLeft: `4px solid ${getSeverityColor(event.severity)}`,
                    background: selectedEvent?.id === event.id ? 'var(--bg-tertiary)' : 'transparent',
                  }}
                >
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                    <span style={{fontSize: 12, color: getSeverityColor(event.severity)}}>
                      {EVENT_TYPE_LABELS[event.type] || event.type}
                    </span>
                    <span style={{fontSize: 11, color: 'var(--text-secondary)'}}>
                      {new Date(event.created_at).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                  <div style={{fontWeight: 500, marginTop: 4}}>{event.title}</div>
                  <div style={{fontSize: 11, color: 'var(--text-secondary)', marginTop: 4}}>
                    {t('timeline.severity', '严重程度')}: {(event.severity * 100).toFixed(0)}% | 
                    {t('timeline.duration', '持续')}: {event.duration_days}{t('timeline.days', '天')}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 事件详情 */}
        {selectedEvent && (
          <div style={{display: 'flex', flexDirection: 'column', gap: 16}}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">{t('timeline.eventDetails', '事件详情')}</span>
                <button onClick={() => setSelectedEvent(null)} style={{background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)'}}>✕</button>
              </div>
              <div>
                <span style={{fontSize: 12, color: getSeverityColor(selectedEvent.severity), fontWeight: 500}}>
                  {EVENT_TYPE_LABELS[selectedEvent.type] || selectedEvent.type}
                </span>
                <h3 style={{margin: '8px 0'}}>{selectedEvent.title}</h3>
                <p style={{color: 'var(--text-secondary)', fontSize: 13}}>{selectedEvent.body}</p>
              </div>
              <div style={{marginTop: 12, display: 'flex', gap: 16, flexWrap: 'wrap'}}>
                <div>
                  <div style={{fontSize: 11, color: 'var(--text-secondary)'}}>{t('timeline.severity', '严重程度')}</div>
                  <div style={{fontWeight: 600, color: getSeverityColor(selectedEvent.severity)}}>
                    {(selectedEvent.severity * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div style={{fontSize: 11, color: 'var(--text-secondary)'}}>{t('timeline.duration', '持续时间')}</div>
                  <div style={{fontWeight: 600}}>{selectedEvent.duration_days} {t('timeline.days', '天')}</div>
                </div>
              </div>
            </div>

            {priceHistory.length > 0 && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title">{t('timeline.priceChart', '价格走势')}</span>
                  <span style={{fontSize: 12, color: 'var(--text-secondary)'}}>{selectedEvent.affected_assets[0]}</span>
                </div>
                <OHLCChart data={priceHistory} height={250} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
