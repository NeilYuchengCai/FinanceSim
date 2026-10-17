import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { useCurrentWorld } from '../hooks/useCurrentWorld'
import { useToast } from '../components/Toast'

/**
 * 挑战页（P0-2 重写）
 *
 * 数据契约（已与后端核对）：
 * - GET  /api/v1/challenges/templates        -> 模板数组
 * - POST /api/v1/challenges?world_id&challenge_type&name&target_days&constraints&description
 * - GET  /api/v1/challenges/world/{worldId}  -> 该世界的挑战列表
 * - GET  /api/v1/challenges/{id}/progress    -> 进度记录数组
 */

interface ChallengeTemplate {
  id: string
  title: string
  description: string
  target_days: number
  constraints: Record<string, unknown> | null
  reward: string
}

interface WorldChallenge {
  id: number
  type: string
  name: string
  description: string | null
  target_days: number
  constraints: Record<string, unknown> | null
  status: string
  created_at: string
  completed_at: string | null
}

interface ProgressEntry {
  day: number
  metrics: Record<string, unknown> | null
  notes: string | null
  recorded_at: string
}

function formatDateTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function formatConstraints(constraints: Record<string, unknown> | null): string {
  if (!constraints || Object.keys(constraints).length === 0) return '—'
  return Object.entries(constraints)
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
    .join(' · ')
}

function toErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return `${t('common.error', 'Error')}: ${err.message}`
  }
  if (err instanceof Error) return `${t('common.error', 'Error')}: ${err.message}`
  return t('common.error', 'Error')
}

const STATUS_TAG_CLASS: Record<string, string> = {
  active: 'tag-blue',
  completed: 'tag-green',
  failed: 'tag-red',
}

export default function Challenges() {
  const { worldId } = useCurrentWorld()
  const toast = useToast()

  const [templates, setTemplates] = useState<ChallengeTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(true)
  const [templatesError, setTemplatesError] = useState<string | null>(null)

  const [challenges, setChallenges] = useState<WorldChallenge[]>([])
  const [challengesLoading, setChallengesLoading] = useState(true)
  const [challengesError, setChallengesError] = useState<string | null>(null)

  const [startingId, setStartingId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [progress, setProgress] = useState<ProgressEntry[]>([])
  const [progressLoading, setProgressLoading] = useState(false)
  const [progressError, setProgressError] = useState<string | null>(null)

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true)
    setTemplatesError(null)
    try {
      const res = await axios.get<ChallengeTemplate[]>('/api/v1/challenges/templates')
      setTemplates(Array.isArray(res.data) ? res.data : [])
    } catch {
      setTemplatesError(t('common.dataError', '数据加载失败'))
    } finally {
      setTemplatesLoading(false)
    }
  }, [])

  const loadChallenges = useCallback(async () => {
    setChallengesLoading(true)
    setChallengesError(null)
    try {
      const res = await axios.get<WorldChallenge[]>(`/api/v1/challenges/world/${worldId}`)
      setChallenges(Array.isArray(res.data) ? res.data : [])
    } catch {
      setChallengesError(t('common.dataError', '数据加载失败'))
    } finally {
      setChallengesLoading(false)
    }
  }, [worldId])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  useEffect(() => {
    loadChallenges()
  }, [loadChallenges])

  const startChallenge = async (template: ChallengeTemplate) => {
    setStartingId(template.id)
    try {
      await axios.post('/api/v1/challenges', null, {
        params: {
          world_id: worldId,
          challenge_type: template.id,
          name: template.title,
          target_days: template.target_days,
          constraints: JSON.stringify(template.constraints ?? {}),
          description: template.description,
        },
      })
      toast.success(`${template.title} ${t('challenges.started', '挑战已开始')}`)
      await loadChallenges()
    } catch (err) {
      toast.error(toErrorMessage(err))
    } finally {
      setStartingId(null)
    }
  }

  const toggleProgress = async (challenge: WorldChallenge) => {
    if (expandedId === challenge.id) {
      setExpandedId(null)
      setProgress([])
      setProgressError(null)
      return
    }
    setExpandedId(challenge.id)
    setProgressLoading(true)
    setProgressError(null)
    try {
      const res = await axios.get<ProgressEntry[]>(`/api/v1/challenges/${challenge.id}/progress`)
      setProgress(Array.isArray(res.data) ? res.data : [])
    } catch {
      setProgress([])
      setProgressError(t('common.dataError', '数据加载失败'))
    } finally {
      setProgressLoading(false)
    }
  }

  const statusLabel = (status: string): string => {
    if (status === 'completed') return t('challenges.statusCompleted', '已完成')
    if (status === 'active') return t('challenges.statusActive', '进行中')
    return status
  }

  const header = (
    <div className="page-header">
      <h2>🏆 {t('challenges.title')}</h2>
      <p className="subtitle">{t('challenges.subtitle', '完成指定投资目标，测试交易技能')}</p>
    </div>
  )

  return (
    <div>
      {header}

      {/* 挑战模板 */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">{t('challenges.templates', '挑战模板')}</span>
          <button className="btn btn-sm" onClick={loadTemplates}>{t('common.refresh')}</button>
        </div>
        {templatesLoading ? (
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        ) : templatesError ? (
          <div className="error" style={{ padding: 20 }}>{templatesError}</div>
        ) : templates.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            {t('common.noData', '暂无数据')}
          </div>
        ) : (
          <div className="grid-3" style={{ padding: 20 }}>
            {templates.map((template) => (
              <div key={template.id} className="card" style={{ textAlign: 'left', padding: 20 }}>
                <h3 style={{ margin: '0 0 8px' }}>{template.title}</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: 13, minHeight: 40 }}>
                  {template.description}
                </p>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  {t('challenges.targetDays', '目标天数')}: <strong>{template.target_days}</strong>
                  {' · '}
                  {t('challenges.reward', '奖励')}: <strong>{template.reward}</strong>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                  {t('challenges.constraints', '挑战条件')}: {formatConstraints(template.constraints)}
                </div>
                <button
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  disabled={startingId === template.id}
                  onClick={() => startChallenge(template)}
                >
                  {startingId === template.id
                    ? t('common.loading', '加载中...')
                    : t('challenges.start', '开始挑战')}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 进行中的挑战 */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <span className="card-title">{t('challenges.yourProgress', '您的进度')}</span>
          <button className="btn btn-sm" onClick={loadChallenges}>{t('common.refresh')}</button>
        </div>
        {challengesLoading ? (
          <div className="loading" style={{ padding: 40 }}>{t('common.loading')}</div>
        ) : challengesError ? (
          <div className="error" style={{ padding: 20 }}>{challengesError}</div>
        ) : challenges.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            {t('challenges.noChallenges', '暂无进行中的挑战，选择一个模板开始吧')}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {challenges.map((challenge) => (
              <div
                key={challenge.id}
                className="card"
                style={{ marginBottom: 0, padding: 16, cursor: 'pointer' }}
                onClick={() => toggleProgress(challenge)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                  <div>
                    <strong>{challenge.name}</strong>
                    <span className={`tag ${STATUS_TAG_CLASS[challenge.status] ?? 'tag-blue'}`} style={{ marginLeft: 8 }}>
                      {statusLabel(challenge.status)}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {expandedId === challenge.id
                      ? t('challenges.hideProgress', '收起进度')
                      : t('challenges.viewProgress', '查看进度')}
                  </span>
                </div>
                {challenge.description && (
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6 }}>
                    {challenge.description}
                  </div>
                )}
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>
                  {t('challenges.targetDays', '目标天数')}: {challenge.target_days}
                  {' · '}
                  {t('challenges.createdAt', '创建时间')}: {formatDateTime(challenge.created_at)}
                  {challenge.completed_at
                    ? ` · ${t('challenges.completedAt', '完成时间')}: ${formatDateTime(challenge.completed_at)}`
                    : ''}
                </div>

                {expandedId === challenge.id && (
                  <div style={{ marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                      {t('challenges.progressTitle', '挑战进度')}
                    </div>
                    {progressLoading ? (
                      <div className="loading" style={{ padding: 16 }}>{t('common.loading')}</div>
                    ) : progressError ? (
                      <div className="error" style={{ padding: 12 }}>{progressError}</div>
                    ) : progress.length === 0 ? (
                      <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
                        {t('challenges.noProgress', '该挑战还没有进度记录')}
                      </div>
                    ) : (
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>{t('simulation.dayPrefix', '第')}</th>
                            <th>{t('challenges.notes', '备注')}</th>
                            <th>{t('challenges.recordedAt', '记录时间')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {progress.map((entry, index) => (
                            <tr key={`${entry.day}-${index}`}>
                              <td>
                                {t('challenges.day', '第')} {entry.day} {t('challenges.daySuffix', '天')}
                              </td>
                              <td>
                                {entry.notes && entry.notes.trim()
                                  ? entry.notes
                                  : entry.metrics && Object.keys(entry.metrics).length > 0
                                    ? JSON.stringify(entry.metrics)
                                    : '—'}
                              </td>
                              <td>{formatDateTime(entry.recorded_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
