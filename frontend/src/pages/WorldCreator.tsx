import { useState, useEffect } from 'react'
import axios from 'axios'

interface World {
  id: number
  name: string
  mode: string
  current_day: number
  seed: string
  created_at: string
}

interface Snapshot {
  id: number
  world_id: number
  name: string
  description: string | null
  snapshot_day: number
  created_at: string
  summary: Record<string, any>
}

export default function WorldCreator() {
  const [worlds, setWorlds] = useState<World[]>([])
  const [selectedWorld, setSelectedWorld] = useState<World | null>(null)
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [snapshotName, setSnapshotName] = useState('')
  const [branchName, setBranchName] = useState('')
  const [branchingSnapshotId, setBranchingSnapshotId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'list' | 'manage'>('list')

  const fetchWorlds = async () => {
    try {
      const res = await axios.get('/api/worlds')
      setWorlds(res.data || [])
    } catch (e) {
      console.error('Failed to fetch worlds:', e)
    }
  }

  useEffect(() => {
    fetchWorlds()
  }, [])

  const fetchSnapshots = async (worldId: number) => {
    try {
      const res = await axios.get(`/api/worlds/${worldId}/snapshots`)
      setSnapshots(res.data || [])
    } catch (e) {
      console.error('Failed to fetch snapshots:', e)
    }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await axios.post('/api/worlds', { name: newName, mode: 'simulation' })
      setNewName('')
      await fetchWorlds()
    } catch (e) {
      console.error('Failed to create world:', e)
    } finally {
      setCreating(false)
    }
  }

  const handleSelectWorld = async (world: World) => {
    setSelectedWorld(world)
    setActiveTab('manage')
    fetchSnapshots(world.id)
  }

  const handleCreateSnapshot = async () => {
    if (!snapshotName.trim() || !selectedWorld) return
    try {
      await axios.post(`/api/worlds/${selectedWorld.id}/snapshots?name=${encodeURIComponent(snapshotName)}`)
      setSnapshotName('')
      await fetchSnapshots(selectedWorld.id)
    } catch (e) {
      console.error('Failed to create snapshot:', e)
    }
  }

  const handleRestore = async (snapshotId: number) => {
    if (!selectedWorld) return
    if (!confirm(`Restore world to snapshot "${snapshots.find(s => s.id === snapshotId)?.name}"? This will discard progress after day ${snapshots.find(s => s.id === snapshotId)?.snapshot_day}.`)) return
    try {
      await axios.post(`/api/worlds/${selectedWorld.id}/snapshots/${snapshotId}/restore`)
      await fetchWorlds()
      await fetchSnapshots(selectedWorld.id)
    } catch (e) {
      console.error('Failed to restore:', e)
    }
  }

  const handleBranch = async (snapshotId: number) => {
    if (!selectedWorld || !branchName.trim()) return
    try {
      await axios.post(
        `/api/worlds/${selectedWorld.id}/snapshots/${snapshotId}/branch?new_world_name=${encodeURIComponent(branchName)}`
      )
      setBranchName('')
      setBranchingSnapshotId(null)
      await fetchWorlds()
    } catch (e) {
      console.error('Failed to branch:', e)
    }
  }

  const handleDeleteWorld = async (worldId: number) => {
    if (!confirm('Delete this world and all its data?')) return
    try {
      await axios.delete(`/api/worlds/${worldId}`)
      setWorlds(prev => prev.filter(w => w.id !== worldId))
      if (selectedWorld?.id === worldId) {
        setSelectedWorld(null)
        setActiveTab('list')
        setSnapshots([])
        setBranchingSnapshotId(null)
      }
    } catch (e) {
      console.error('Failed to delete world:', e)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>🌐 World Manager</h2>
        <p className="subtitle">Create, manage, and branch simulation worlds</p>
      </div>

      {/* Create World */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Create New World</span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            type="text"
            className="input-field"
            placeholder="World name..."
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
            style={{ flex: 1 }}
          />
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>

      {/* World List / Manage Toggle */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Your Worlds ({worlds.length})</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className={`btn ${activeTab === 'list' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('list')}
            >List</button>
            {selectedWorld && (
              <button
                className={`btn ${activeTab === 'manage' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => { setActiveTab('manage'); fetchSnapshots(selectedWorld.id) }}
              >Manage</button>
            )}
          </div>
        </div>
      </div>

      {activeTab === 'list' && (
        <div className="grid-3">
          {worlds.length === 0 ? (
            <div className="card" style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🌐</div>
              <p style={{ color: 'var(--text-secondary)' }}>No worlds yet. Create one above to get started.</p>
            </div>
          ) : worlds.map(world => (
            <div key={world.id} className="card" style={{ cursor: 'pointer', transition: 'all 0.2s' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>{world.name}</h3>
                  <span className={`tag tag-${world.mode === 'challenge' ? 'red' : 'blue'}`}>
                    {world.mode}
                  </span>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); handleDeleteWorld(world.id) }}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--accent-red)', fontSize: 16 }}
                >✕</button>
              </div>
              <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
                <div>Day: <strong style={{ color: 'var(--text-primary)' }}>{world.current_day}</strong></div>
                <div>Seed: <strong style={{ color: 'var(--text-primary)' }}>{world.seed}</strong></div>
              </div>
              <button className="btn btn-primary" style={{ marginTop: 16, width: '100%' }} onClick={() => handleSelectWorld(world)}>
                Manage World
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'manage' && selectedWorld && (
        <div>
          {/* World Header */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ margin: 0 }}>{selectedWorld.name}</h2>
                <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                  Day {selectedWorld.current_day} · Seed: {selectedWorld.seed} · Mode: {selectedWorld.mode}
                </span>
              </div>
            </div>
          </div>

          {/* Snapshot Creation */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">💾 Create Snapshot</span>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <input
                type="text"
                className="input-field"
                placeholder="Snapshot name (e.g. Day 100 milestone)"
                value={snapshotName}
                onChange={e => setSnapshotName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreateSnapshot()}
                style={{ flex: 1 }}
              />
              <button className="btn btn-primary" onClick={handleCreateSnapshot}>
                Save Snapshot
              </button>
            </div>
          </div>

          {/* Snapshots List */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">📸 Snapshots ({snapshots.length})</span>
            </div>
            {snapshots.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)' }}>
                No snapshots yet. Save your first one above.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Day</th>
                    <th>Created</th>
                    <th>Assets</th>
                    <th>Events</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshots.map(snap => (
                    <tr key={snap.id}>
                      <td>
                        <strong>{snap.name}</strong>
                        {snap.description && (
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{snap.description}</div>
                        )}
                      </td>
                      <td><span className="tag tag-blue">Day {snap.snapshot_day}</span></td>
                      <td>{new Date(snap.created_at).toLocaleString()}</td>
                      <td>{snap.summary?.asset_count ?? '-'}</td>
                      <td>{snap.summary?.event_count ?? '-'}</td>
                      <td style={{ display: 'flex', gap: 8 }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '4px 10px', fontSize: 12 }}
                          onClick={() => handleRestore(snap.id)}
                        >↩ Restore</button>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '4px 10px', fontSize: 12 }}
                          onClick={() => {
                            if (branchingSnapshotId === snap.id) {
                              setBranchingSnapshotId(null)
                              setBranchName('')
                            } else {
                              setBranchingSnapshotId(snap.id)
                              setBranchName('')
                            }
                          }}
                        >🌿 Branch</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Branch Input */}
          {branchingSnapshotId !== null && (
            <div className="card" style={{ marginTop: 16, borderColor: 'var(--accent-yellow)' }}>
              <div className="card-header">
                <span className="card-title">🌿 Branch from Snapshot</span>
                <button className="btn btn-secondary" onClick={() => { setBranchingSnapshotId(null); setBranchName('') }}>✕</button>
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                <input
                  type="text"
                  className="input-field"
                  placeholder="New world name..."
                  value={branchName}
                  onChange={e => setBranchName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleBranch(branchingSnapshotId)}
                  style={{ flex: 1 }}
                />
                <button className="btn btn-primary" onClick={() => handleBranch(branchingSnapshotId)}>Create Branch</button>
              </div>
              <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
                Creates a new world starting from this snapshot&apos;s state. The original world is unchanged.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
