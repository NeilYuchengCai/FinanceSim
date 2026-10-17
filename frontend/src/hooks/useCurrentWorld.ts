import { useCallback, useEffect, useState } from 'react'

/**
 * 多世界上下文（Wave 1 地基）
 *
 * 全局唯一「当前世界」来源：
 * - localStorage key: 'financesim-world-id'（与 WorldCreator 原有 key 保持一致）
 * - 同一标签页内通过自定义事件 'financesim-world-changed' 广播
 * - 跨标签页通过浏览器原生 'storage' 事件同步
 *
 * 读取策略：非法值 / 解析失败 / 存储不可用一律回退默认世界 1。
 */

export const WORLD_ID_STORAGE_KEY = 'financesim-world-id'
export const WORLD_CHANGED_EVENT = 'financesim-world-changed'
export const DEFAULT_WORLD_ID = 1

/** 从 localStorage 读取当前世界 id；任何异常都安全回退到默认世界。 */
export function readWorldIdFromStorage(): number {
  try {
    const raw = window.localStorage.getItem(WORLD_ID_STORAGE_KEY)
    if (!raw) return DEFAULT_WORLD_ID
    const parsed = Number.parseInt(raw, 10)
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_WORLD_ID
  } catch {
    return DEFAULT_WORLD_ID
  }
}

export interface CurrentWorld {
  worldId: number
  setWorldId: (id: number) => void
}

/**
 * 订阅「当前世界」。setWorldId 会写 localStorage 并广播
 * 'financesim-world-changed'，同页面所有订阅方（含本 hook 的其他实例）立即刷新。
 */
export function useCurrentWorld(): CurrentWorld {
  const [worldId, setWorldIdState] = useState<number>(readWorldIdFromStorage)

  useEffect(() => {
    const onChange = () => setWorldIdState(readWorldIdFromStorage())
    window.addEventListener('storage', onChange)
    window.addEventListener(WORLD_CHANGED_EVENT, onChange)
    return () => {
      window.removeEventListener('storage', onChange)
      window.removeEventListener(WORLD_CHANGED_EVENT, onChange)
    }
  }, [])

  const setWorldId = useCallback((id: number) => {
    const next = Number.isFinite(id) && id > 0 ? Math.floor(id) : DEFAULT_WORLD_ID
    try {
      window.localStorage.setItem(WORLD_ID_STORAGE_KEY, String(next))
    } catch {
      // 隐私模式等场景下存储不可用：仅保留内存状态，不阻断切换
    }
    setWorldIdState(next)
    window.dispatchEvent(new Event(WORLD_CHANGED_EVENT))
  }, [])

  return { worldId, setWorldId }
}
