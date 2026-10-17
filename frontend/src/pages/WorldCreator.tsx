import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { useCurrentWorld, DEFAULT_WORLD_ID } from '../hooks/useCurrentWorld'
import { useToast } from '../components/Toast'

interface World {
  id: number
  name: string
  mode: string
  seed: string | null
  current_day: number
  created_at: string
}

const MODE_CARDS = [
  {
    mode: 'demo',
    icon: '🎮',
    labelKey: 'world.demo',
    fallback: 'Demo Mode',
    defaultName: 'Demo World',
    descKey: 'world.demoDesc',
    descFallback: 'Guided walkthrough with preset scenarios',
  },
  {
    mode: 'sandbox',
    icon: '🔬',
    labelKey: 'world.sandbox',
    fallback: 'Sandbox Mode',
    defaultName: 'Sandbox World',
    descKey: 'world.sandboxDesc',
    descFallback: 'Free-form experimentation with no constraints',
  },
  {
    mode: 'competitive',
    icon: '🏆',
    labelKey: 'world.competitive',
    fallback: 'Competitive Mode',
    defaultName: 'Competitive World',
    descKey: 'world.competitiveDesc',
    descFallback: 'Ranked runs scored against other agents',
  },
]

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function toErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return `${t('common.error')}: ${err.message}`
  }
  if (err instanceof Error) return `${t('common.error')}: ${err.message}`
  return t('common.error')
}

export default function WorldCreator() {
  const [worlds, setWorlds] = useState<World[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { worldId: currentWorldId, setWorldId } = useCurrentWorld()
  const toast = useToast()
  const [creatingMode, setCreatingMode] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  // 删除二次确认：自定义深色 modal（替代 window.confirm，保证主题一致）
  const [deleteTarget, setDeleteTarget] = useState<World | null>(null)

  const loadWorlds = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get<World[]>('/api/v1/worlds')
      setWorlds(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setError(toErrorMessage(err))
      setWorlds([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadWorlds()
  }, [loadWorlds])

  // Fall back to the default world when the selected one no longer exists.
  useEffect(() => {
    if (loading || worlds.length === 0) return
    if (!worlds.some(w => w.id === currentWorldId)) {
      setWorldId(DEFAULT_WORLD_ID)
    }
  }, [loading, worlds, currentWorldId, setWorldId])

  const selectWorld = (worldId: number) => {
    setWorldId(worldId)
    const target = worlds.find(w => w.id === worldId)
    toast.success(`${target ? target.name : `#${worldId}`} ${t('world.selected')}`)
  }

  const createWorld = async (mode: string, fallbackName: string) => {
    setCreatingMode(mode)
    try {
      const baseName = fallbackName
      const existing = worlds.filter(w => w.name === baseName || w.name.startsWith(`${baseName} `)).length
      const name = existing === 0 ? baseName : `${baseName} ${existing + 1}`

      const res = await axios.post<World>('/api/v1/worlds', { name, mode, seed: null })
      await loadWorlds()
      // 创建成功后立即切到新世界，后续页面请求都会带上新 world_id
      if (res.data && Number.isFinite(res.data.id)) {
        setWorldId(res.data.id)
      }
      toast.success(`${name} ${t('world.created')}`)
    } catch (err) {
      toast.error(toErrorMessage(err))
    } finally {
      setCreatingMode(null)
    }
  }

  // 打开自定义确认弹窗（不再使用 window.confirm）
  const requestDeleteWorld = (world: World) => {
    setDeleteTarget(world)
  }

  const closeDeleteModal = () => {
    if (deletingId !== null) return // 删除进行中不允许关闭
    setDeleteTarget(null)
  }

  const confirmDeleteWorld = async () => {
    const world = deleteTarget
    if (!world) return

    setDeletingId(world.id)
    try {
      await axios.delete(`/api/v1/worlds/${encodeURIComponent(String(world.id))}`)
      await loadWorlds()
      // 删除的正是当前世界时回退到默认世界，避免后续请求指向已删除的 id
      if (world.id === currentWorldId) {
        setWorldId(DEFAULT_WORLD_ID)
      }
      toast.success(`${world.name} ${t('world.deleted')}`)
      setDeleteTarget(null)
    } catch (err) {
      toast.error(toErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>🌐 {t('world.title')}</h2>
        <p className="subtitle">
          {t('world.subtitle')}
        </p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('world.createTitle')}</span>
          <span className="tag tag-blue">{t('world.selectHint')}</span>
        </div>
        <div className="grid-3" style={{ padding: 20 }}>
          {MODE_CARDS.map(item => (
            <div
              key={item.mode}
              className="card"
              style={{
                textAlign: 'center',
                padding: 32,
                cursor: creatingMode ? 'progress' : 'pointer',
                opacity: creatingMode && creatingMode !== item.mode ? 0.5 : 1,
                pointerEvents: creatingMode ? 'none' : 'auto',
              }}
              onClick={() => createWorld(item.mode, item.defaultName)}
            >
              <div style={{ fontSize: 48, marginBottom: 12 }}>{item.icon}</div>
              <h3 style={{ margin: '0 0 8px' }}>{t(item.labelKey, item.fallback)}</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                {creatingMode === item.mode
                  ? t('common.loading')
                  : t(item.descKey, item.descFallback)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('world.worlds')}</span>
          <span className="tag tag-blue">{loading ? '...' : worlds.length}</span>
        </div>

        {loading ? (
          <div className="loading" style={{ padding: 40 }}>
            {t('common.loading')}
          </div>
        ) : error ? (
          <div style={{ padding: 20 }}>
            <div
              className="error"
              style={{
                padding: 20,
                color: 'var(--accent-red)',
                background: 'rgba(248, 81, 73, 0.10)',
                borderRadius: 6,
              }}
            >
              {error}
            </div>
            <button className="btn" style={{ marginTop: 12 }} onClick={() => loadWorlds()}>
              {t('common.retry')}
            </button>
          </div>
        ) : worlds.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            {t('world.noWorlds')}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>{t('world.fieldId')}</th>
                  <th>{t('world.fieldName')}</th>
                  <th>{t('world.fieldMode')}</th>
                  <th>{t('world.fieldSeed')}</th>
                  <th>{t('world.fieldDay')}</th>
                  <th>{t('world.fieldCreated')}</th>
                  <th>{t('world.fieldActions')}</th>
                </tr>
              </thead>
              <tbody>
                {worlds.map(world => {
                  const isCurrent = world.id === currentWorldId
                  return (
                    <tr
                      key={world.id}
                      onClick={() => !isCurrent && selectWorld(world.id)}
                      style={{
                        cursor: isCurrent ? 'default' : 'pointer',
                        background: isCurrent ? 'rgba(88, 166, 255, 0.10)' : undefined,
                        outline: isCurrent ? '1px solid var(--accent-blue)' : undefined,
                      }}
                    >
                      <td>{world.id}</td>
                      <td>
                        <strong>{world.name}</strong>
                        {isCurrent && (
                          <span className="tag tag-blue" style={{ marginLeft: 8 }}>
                            {t('world.current')}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className="tag">{world.mode}</span>
                      </td>
                      <td>{world.seed ?? '-'}</td>
                      <td>{world.current_day}</td>
                      <td>{formatDate(world.created_at)}</td>
                      <td>
                        <button
                          className="btn"
                          style={{
                            color: 'var(--accent-red)',
                            background: 'rgba(248, 81, 73, 0.10)',
                            border: '1px solid rgba(248, 81, 73, 0.4)',
                            opacity: deletingId === world.id ? 0.6 : 1,
                          }}
                          disabled={deletingId === world.id}
                          onClick={e => {
                            e.stopPropagation()
                            requestDeleteWorld(world)
                          }}
                        >
                          {deletingId === world.id
                            ? t('common.loading')
                            : t('common.delete')}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 删除世界二次确认弹窗（深色主题，与全局 CSS 变量一致） */}
      {deleteTarget && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={closeDeleteModal}
        >
          <div
            className="card"
            style={{
              width: 420,
              maxWidth: '90vw',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 8,
              padding: 24,
            }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 12px', color: 'var(--text-primary)' }}>
              {deleteTarget.id === DEFAULT_WORLD_ID
                ? t('world.confirmDeleteDefault')
                : t('world.confirmDelete')}
            </h3>
            <p style={{ margin: '0 0 8px', color: 'var(--text-primary)' }}>
              “{deleteTarget.name}”
            </p>
            {deleteTarget.id === DEFAULT_WORLD_ID && (
              <p style={{ margin: '0 0 8px', color: 'var(--accent-red)', fontSize: 13 }}>
                {t('world.confirmDeleteHint')}
              </p>
            )}
            <p style={{ margin: '0 0 20px', color: 'var(--text-secondary)', fontSize: 13 }}>
              {t('world.deleteWarning')}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button className="btn btn-secondary" onClick={closeDeleteModal} disabled={deletingId !== null}>
                {t('common.cancel')}
              </button>
              <button
                className="btn"
                style={{
                  color: 'var(--accent-red)',
                  background: 'rgba(248, 81, 73, 0.10)',
                  border: '1px solid rgba(248, 81, 73, 0.4)',
                  opacity: deletingId !== null ? 0.6 : 1,
                }}
                onClick={confirmDeleteWorld}
                disabled={deletingId !== null}
              >
                {deletingId !== null ? t('common.loading') : t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
