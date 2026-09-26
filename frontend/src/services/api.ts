import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

export interface Asset {
  id: number
  ticker: string
  type: string
  name: string
  exchange: string
  sector: string
  industry: string
  currency: string
  market_cap: number
  beta: number
  volatility: number
  fundamentals: Record<string, any>
}

export interface PriceBar {
  id: number
  asset_id: number
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface FXPair {
  ticker: string
  base: string
  quote: string
  price: number
  spread: number
  volatility: number
  change_24h: number
  high_24h: number
  low_24h: number
}

export interface Commodity {
  ticker: string
  name: string
  category: string
  current_price: number
  change_24h: number
  high_24h: number
  low_24h: number
}

export interface Bond {
  id: number
  ticker: string
  name: string
  yield: number
  duration: number
  price: number
  change_24h: number
}

// Assets API
export const assetsApi = {
  list: async (worldId: number, type?: string, limit = 500) => {
    const params = new URLSearchParams({ world_id: String(worldId), limit: String(limit) })
    if (type) params.append('type', type)
    const res = await api.get(`/assets?${params}`)
    return res.data as Asset[]
  },
  
  get: async (ticker: string, worldId: number) => {
    const res = await api.get(`/assets/${ticker}?world_id=${worldId}`)
    return res.data as Asset
  },
  
  getHistory: async (ticker: string, worldId: number, limit = 100) => {
    const res = await api.get(`/assets/${ticker}/history?world_id=${worldId}&limit=${limit}`)
    return res.data as PriceBar[]
  },
}

// FX API
export const fxApi = {
  listPairs: async () => {
    const res = await api.get('/fx/pairs')
    return res.data as FXPair[]
  },
  
  getPair: async (ticker: string) => {
    const res = await api.get(`/fx/pair/${ticker}`)
    return res.data as FXPair
  },
  
  getHistory: async (ticker: string, limit = 100) => {
    const res = await api.get(`/fx/pair/${ticker}/history?limit=${limit}`)
    return res.data as PriceBar[]
  },
}

// Commodities API
export const commoditiesApi = {
  list: async (worldId: number) => {
    const res = await api.get(`/commodities?world_id=${worldId}`)
    return res.data as Commodity[]
  },
  
  get: async (ticker: string) => {
    const res = await api.get(`/commodities/${ticker}`)
    return res.data as Commodity
  },
}

// Bonds API
export const bondsApi = {
  list: async (worldId: number) => {
    const res = await api.get(`/bonds?world_id=${worldId}`)
    return res.data as Bond[]
  },
  
  getYieldCurve: async () => {
    const res = await api.get('/bonds/yield-curve')
    return res.data
  },
}

// Economy API
export const economyApi = {
  getState: async () => {
    const res = await api.get('/economy/state')
    return res.data
  },
  
  getIndicators: async () => {
    const res = await api.get('/economy/indicators')
    return res.data
  },
  
  step: async (days = 1) => {
    const res = await api.post(`/economy/step?days=${days}`)
    return res.data
  },
}

// News API
export const newsApi = {
  headlines: async () => {
    const res = await api.get('/news/headlines')
    return res.data
  },
  
  get: async (id: string) => {
    const res = await api.get(`/news/${id}`)
    return res.data
  },
}

// World API
export const worldApi = {
  list: async () => {
    const res = await api.get('/worlds')
    return res.data
  },
  
  get: async (id: number) => {
    const res = await api.get(`/worlds/${id}`)
    return res.data
  },
}

export default api
