import { useState, useEffect } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { readWorldIdFromStorage } from '../hooks/useCurrentWorld'

const STORAGE_KEY_PREFIX = 'financesim-save-'

export interface SaveSlot {
  id: string
  name: string
  timestamp: string
  day: number
  speed: string
  isPaused: boolean
}

// 生成唯一ID
function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

// 保存世界状态到localStorage
// worldId 不传时读取当前选中的世界（localStorage 'financesim-world-id'，非法值回退 1）
export async function saveWorld(name: string, worldId?: number): Promise<string> {
  const targetWorldId = worldId ?? readWorldIdFromStorage()
  try {
    const statusRes = await axios.get(`/api/v1/simulation/${targetWorldId}/status`)
    const assetsRes = await axios.get(`/api/v1/assets?world_id=${targetWorldId}`)
    const economyRes = await axios.get('/api/v1/economy/state')
    
    const saveData = {
      id: generateId(),
      name,
      timestamp: new Date().toISOString(),
      simulation: statusRes.data,
      assets: assetsRes.data,
      economy: economyRes.data,
    }
    
    localStorage.setItem(`${STORAGE_KEY_PREFIX}${saveData.id}`, JSON.stringify(saveData))
    return saveData.id
  } catch (error) {
    console.error('Failed to save world:', error)
    throw error
  }
}

// 从localStorage加载世界状态
// worldId 不传时读取当前选中的世界（与 saveWorld 一致）
export async function loadWorld(saveId: string, worldId?: number): Promise<boolean> {
  const targetWorldId = worldId ?? readWorldIdFromStorage()
  try {
    const data = localStorage.getItem(`${STORAGE_KEY_PREFIX}${saveId}`)
    if (!data) return false
    
    const saveData = JSON.parse(data)
    const sim = saveData.simulation || {}
    const targetDay = sim.current_day || 0
    
    // 1. 重置模拟时钟后再步进到目标天数，恢复模拟时间
    await axios.post(`/api/v1/simulation/${targetWorldId}/reset`)
    if (targetDay > 0) {
      await axios.post(`/api/v1/simulation/${targetWorldId}/step`, null, { params: { days: targetDay } })
    }
    
    // 2. 恢复速度设定
    if (sim.speed) {
      await axios.post(`/api/v1/simulation/${targetWorldId}/speed`, null, { params: { speed: sim.speed } })
    }
    
    // 3. 按存档中记录的价格恢复资产（通过 ticker 匹配内存行情流）
    const savedAssets: any[] = saveData.assets || []
    for (const a of savedAssets) {
      if (a.ticker && typeof a.current_price === 'number') {
        try {
          await axios.put(`/api/v1/assets/${a.ticker}/price`, null, {
            params: { price: a.current_price, world_id: targetWorldId }
          })
        } catch {
          // 个别资产可能不在行情流中，忽略
        }
      }
    }
    
    // 4. 恢复运行/暂停状态
    if (sim.is_paused) {
      await axios.post(`/api/v1/simulation/${targetWorldId}/pause`)
    } else {
      await axios.post(`/api/v1/simulation/${targetWorldId}/start`)
    }
    
    return true
  } catch (error) {
    console.error('Failed to load world:', error)
    return false
  }
}

// 获取所有存档列表
export function getSaveList(): SaveSlot[] {
  const saves: SaveSlot[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(STORAGE_KEY_PREFIX)) {
      try {
        const data = JSON.parse(localStorage.getItem(key)!)
        saves.push({
          id: data.id,
          name: data.name,
          timestamp: data.timestamp,
          day: data.simulation?.current_day ?? 0,
          speed: data.simulation?.speed ?? 'X1',
          isPaused: data.simulation?.is_paused ?? true,
        })
      } catch {
        // 跳过损坏的存档
      }
    }
  }
  return saves.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}

// 删除存档
export function deleteSave(saveId: string): boolean {
  const key = `${STORAGE_KEY_PREFIX}${saveId}`
  if (localStorage.removeItem(key)) {
    return true
  }
  return false
}

// 自动存档（每天切换时触发，带 5 秒防抖）
let lastSaveDay = -1
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

export function autoSaveIfNewDay(currentDay: number): void {
  if (currentDay !== lastSaveDay && currentDay > 0) {
    lastSaveDay = currentDay
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      saveWorld(`Auto-Save Day ${currentDay}`).catch(console.error)
    }, 5000)
  }
}

// 初始化时加载最新存档
export async function restoreLatestSave(): Promise<boolean> {
  const saves = getSaveList()
  if (saves.length === 0) return false
  
  const latest = saves[0]
  return await loadWorld(latest.id)
}
