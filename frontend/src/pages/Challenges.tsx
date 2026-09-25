import { useState, useEffect } from 'react'
import axios from 'axios'

interface ChallengeTemplate {
  id: string
  title: string
  description: string
  target_days: number
  constraints: Record<string, any>
  reward: string
}

interface Challenge {
  id: number
  world_id: number
  type: string
  name: string
  description: string | null
  target_days: number
  constraints: Record<string, any>
  status: string
  created_at: string
  completed_at: string | null
}

interface ProgressLog {
  day: number
  metrics: Record<string, any>
  notes: string | null
  recorded_at: string
}

export default function Challenges() {
  const [templates, setTemplates] = useState<ChallengeTemplate[]>([])
  const [challenges, setChallenges] = useState<Challenge[]>([])
  const [progress, setProgress] = useState<ProgressLog[]>([])
  const [selectedWorld, setSelectedWorld] = useState<number | null>(null)
  const [worlds, setWorlds] = useState<{ id: number; name: string }[]>([])
  const [creating, setCreating] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'templates' | 'my'>('templates')

  useEffect(() => {
    Promise.all([
      axios.get('/api/challenges/templates').then(r => setTemplates(r.data)),
      axios.get('/api/worlds').then(r => setWorlds(r.data || [])),
    ]).catch(console.error)
  }, [])

  useEffect(() => {
    if (selectedWorld) {
      axios.get(`/api/challenges/world/${selectedWorld}`)
        .then(r => setChallenges(r.data || []))
        .catch(console.error)
    }
  }, [selectedWorld])

  useEffect(() => {
    if (challenges.length > 0) {
      const active = challenges.find(c => c.status === 'active')
      if (active) {
        axios.get(`/api/challenges/${active.id}/progress`)
          .then(r => setProgress(r.data || []))
          .catch(console.error)
      }
    }
  }, [challenges])

  const handleCreateChallenge = async (templateId: string) => {
    if (!selectedWorld) return
    const template = templates.find(t => t.id === templateId)
    if (!template) return
    setCreating(true)
    try {
      await axios.post(
        `/api/challenges?world_id=${selectedWorld}&challenge_type=${templateId}&name=${encodeURIComponent(template.title)}&description=${encodeURIComponent(template.description)}&target_days=${template.target_days}&constraints=${encodeURIComponent(JSON.stringify(template.constraints))}`
      )
      setSelectedTemplate('')
      if (selectedWorld) {
        axios.get(`/api/challenges/world/${selectedWorld}`)
          .then(r => setChallenges(r.data || []))
          .catch(console.error)
      }
    } catch (e) {
      console.error('Failed to create challenge:', e)
    } finally {
      setCreating(false)
    }
  }

  // const _logProgress = async (_challengeId: number, _day: number, _metrics: Record<string, any>) => {}

  // const activeChallenge = challenges.find(c => c.status === 'active')

  return (
    <div>
      <div className="page-header">
        <h2>🏆 Challenges</h2>
        <p className="subtitle">Test your trading skills with special objectives</p>
      </div>

      {/* World Selector */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Select World</span>
        </div>
        <select
          className="input-field"
          style={{ width: 'auto' }}
          value={selectedWorld ?? ''}
          onChange={e => setSelectedWorld(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">-- Choose a world --</option>
          {worlds.map(w => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button
          className={`btn ${activeTab === 'templates' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('templates')}
        >Templates</button>
        <button
          className={`btn ${activeTab === 'my' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('my')}
        >My Challenges</button>
      </div>

      {activeTab === 'templates' && (
        <div className="grid-2">
          {templates.map(template => (
            <div key={template.id} className="card">
              <div className="card-header">
                <span className="card-title">{template.title}</span>
                <span className="tag tag-yellow">Day {template.target_days}</span>
              </div>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 12, fontSize: 14 }}>
                {template.description}
              </p>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                <strong>Reward:</strong> {template.reward}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                {Object.entries(template.constraints).map(([k, v]) => (
                  <span key={k} className="tag tag-gray" style={{ marginRight: 4, marginBottom: 4 }}>{k}: {JSON.stringify(v)}</span>
                ))}
              </div>
              <button
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={!selectedWorld || creating || selectedTemplate === template.id}
                onClick={() => handleCreateChallenge(template.id)}
              >
                {selectedTemplate === template.id ? 'Creating...' : 'Start Challenge'}
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'my' && (
        <div>
          {!selectedWorld ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <p style={{ color: 'var(--text-secondary)' }}>Select a world above to view your challenges</p>
            </div>
          ) : challenges.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <p style={{ color: 'var(--text-secondary)' }}>No challenges yet. Switch to Templates to start one.</p>
            </div>
          ) : (
            <div className="grid-2">
              {challenges.map(challenge => (
                <div key={challenge.id} className="card">
                  <div className="card-header">
                    <span className="card-title">{challenge.name}</span>
                    <span className={`tag ${challenge.status === 'completed' ? 'tag-green' : challenge.status === 'failed' ? 'tag-red' : 'tag-blue'}`}>
                      {challenge.status.toUpperCase()}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 8 }}>
                    {challenge.description}
                  </p>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                    Target: Day {challenge.target_days} · Started: {new Date(challenge.created_at).toLocaleDateString()}
                    {challenge.completed_at && ` · Completed: {new Date(challenge.completed_at).toLocaleDateString()}`}
                  </div>
                  {progress.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>Recent Progress</div>
                      {progress.slice(-3).map((p, i) => (
                        <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '4px 0' }}>
                          Day {p.day}: {JSON.stringify(p.metrics)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
