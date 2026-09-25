import { useState, useEffect } from 'react'
import axios from 'axios'
import OHLCChart from '../components/charts/OHLCChart'

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

export default function TimelinePage() {
  const [events, setEvents] = useState<Event[]>([])
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')

  const fetchEvents = async () => {
    try {
      const res = await axios.get('/api/events/list', { params: { world_id: 1, limit: 100 } })
      setEvents(res.data || [])
    } catch (e) {
      console.error('Failed to fetch events:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvents()
  }, [])

  const handleEventClick = async (event: Event) => {
    setSelectedEvent(event)
    if (event.affected_assets.length > 0) {
      try {
        const res = await axios.get('/api/assets/price-history', {
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

  const getEventTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      earnings: '财报',
      product_launch: '新品发布',
      management_change: '管理层变动',
      regulatory: '监管事件',
      ma: '并购',
      guidance: '指引',
      geopolitical: '地缘政治',
      central_bank: '央行决策',
      inflation_shock: '通胀冲击',
      employment_shock: '就业冲击',
      liquidity_crisis: '流动性危机',
      banking_crisis: '银行危机',
      black_swan: '黑天鹅'
    }
    return labels[type] || type
  }

  const filteredEvents = filter === 'ALL' ? events : events.filter(e => e.type === filter)

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0, color: '#fff' }}>📅 事件时间线</h2>
        <button onClick={fetchEvents} style={btnStyle}>刷新</button>
      </div>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        {['ALL', 'earnings', 'geopolitical', 'central_bank', 'liquidity_crisis', 'black_swan'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              ...badgeStyle,
              background: filter === f ? '#6366f1' : '#374151',
              color: '#fff',
              cursor: 'pointer',
              border: 'none',
              padding: '6px 16px',
              borderRadius: '20px',
              fontSize: '13px'
            }}
          >
            {f === 'ALL' ? '全部' : getEventTypeLabel(f)}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedEvent ? '1fr 1fr' : '1fr', gap: '16px' }}>
        {/* 事件列表 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {loading ? (
            <div style={{ ...cardStyle, textAlign: 'center', padding: '40px', color: '#9ca3af' }}>加载中...</div>
          ) : filteredEvents.length === 0 ? (
            <div style={{ ...cardStyle, textAlign: 'center', padding: '40px', color: '#9ca3af' }}>暂无事件</div>
          ) : (
            filteredEvents.map(event => (
              <div
                key={event.id}
                onClick={() => handleEventClick(event)}
                style={{
                  ...cardStyle,
                  cursor: 'pointer',
                  borderLeft: `4px solid ${getSeverityColor(event.severity)}`,
                  background: selectedEvent?.id === event.id ? '#374151' : '#1f2937',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ ...badgeStyle, background: getSeverityColor(event.severity), color: '#fff' }}>
                    {getEventTypeLabel(event.type)}
                  </span>
                  <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                    {new Date(event.created_at).toLocaleDateString()}
                  </span>
                </div>
                <h3 style={{ margin: '8px 0', color: '#fff', fontSize: '14px' }}>{event.title}</h3>
                <p style={{ margin: '4px 0', color: '#6b7280', fontSize: '12px' }}>
                  影响: {event.affected_assets.slice(0, 3).join(', ')}{event.affected_assets.length > 3 ? ` +${event.affected_assets.length - 3}` : ''}
                </p>
                <div style={{ fontSize: '11px', color: '#9ca3af' }}>严重程度: {(event.severity * 100).toFixed(0)}% | 持续: {event.duration_days}天</div>
              </div>
            ))
          )}
        </div>

        {/* 事件详情 + 价格图表 */}
        {selectedEvent && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <span style={{ ...badgeStyle, background: getSeverityColor(selectedEvent.severity), color: '#fff' }}>
                    {getEventTypeLabel(selectedEvent.type)}
                  </span>
                  <h3 style={{ margin: '8px 0', color: '#fff' }}>{selectedEvent.title}</h3>
                  <p style={{ color: '#9ca3af', fontSize: '13px' }}>{selectedEvent.body}</p>
                </div>
                <button onClick={() => setSelectedEvent(null)} style={{ ...iconBtn, background: '#374151' }}>×</button>
              </div>
              <div style={{ marginTop: '12px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <div style={statItemStyle}>
                  <div style={{ fontSize: '11px', color: '#9ca3af' }}>严重程度</div>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: getSeverityColor(selectedEvent.severity) }}>
                    {(selectedEvent.severity * 100).toFixed(0)}%
                  </div>
                </div>
                <div style={statItemStyle}>
                  <div style={{ fontSize: '11px', color: '#9ca3af' }}>持续时间</div>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>{selectedEvent.duration_days} 天</div>
                </div>
                <div style={statItemStyle}>
                  <div style={{ fontSize: '11px', color: '#9ca3af' }}>情绪影响</div>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: (selectedEvent.sentiment_effect || 0) >= 0 ? '#ef4444' : '#22c55e' }}>
                    {((selectedEvent.sentiment_effect || 0) * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
              {selectedEvent.affected_assets.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px' }}>受影响资产</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {selectedEvent.affected_assets.map(t => (
                      <span key={t} style={{ fontSize: '11px', background: '#374151', padding: '2px 8px', borderRadius: '4px', color: '#d1d5db' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {selectedEvent.macro_effect && Object.keys(selectedEvent.macro_effect).length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px' }}>宏观影响</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(selectedEvent.macro_effect).map(([k, v]) => (
                      <span key={k} style={{ fontSize: '11px', background: '#374151', padding: '2px 8px', borderRadius: '4px', color: '#d1d5db' }}>
                        {k}: {(v as number).toFixed(4)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {priceHistory.length > 0 && (
              <div style={cardStyle}>
                <div className="card-header">
                  <span className="card-title">价格走势</span>
                  <span style={{ fontSize: '12px', color: '#9ca3af' }}>{selectedEvent.affected_assets[0]}</span>
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

const cardStyle: React.CSSProperties = {
  background: '#1f2937',
  borderRadius: '12px',
  padding: '16px',
  border: '1px solid #374151'
}

const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: '8px',
  border: 'none',
  background: '#6366f1',
  color: '#fff',
  cursor: 'pointer',
  fontSize: '14px'
}

const badgeStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '4px 12px',
  borderRadius: '20px',
  fontSize: '12px'
}

const iconBtn: React.CSSProperties = {
  width: '28px',
  height: '28px',
  borderRadius: '6px',
  border: 'none',
  color: '#fff',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '18px'
}

const statItemStyle: React.CSSProperties = {
  flex: '1',
  minWidth: '80px'
}
