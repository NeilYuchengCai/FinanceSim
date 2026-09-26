import { useEffect, useState } from 'react'

/**
 * 实时价格流（WebSocket）
 *
 * 后端端点：ws://<当前 host>/api/v1/ws/prices
 * 消息契约：
 *   首帧 {"type":"snapshot","ts":"...","items":[{"t":"AAPL","p":178.53,"c":0.32}]}
 *   增量 {"type":"update",  "ts":"...","items":[...]}   // 只含发生变化的条目，休市时可能为 []
 *
 * 设计要点：
 * 1. 进程内只有一条 WebSocket，多个页面共用；连接一旦建立就保持常驻，
 *    页面切换不会反复重连（这正是"不切换栏目也能一直跳动"的前提）。
 * 2. 订阅是 **按 ticker 粒度** 的：只有价格真正变化的那个单元格会重渲染，
 *    不会整表 455 行每秒重渲染导致闪烁或滚动跳动。
 * 3. 断线指数退避重连（上限 10s），断线期间保留最后已知价格，界面不弹窗。
 */

export interface PriceQuote {
  price: number
  changePct: number
}

type Listener = () => void

const WS_PATH = '/api/v1/ws/prices'
const RECONNECT_BASE_MS = 500
const RECONNECT_MAX_MS = 10_000

function resolveStreamUrl(): string {
  // 用 window.location 推导，部署到非 localhost 后依然可用
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${scheme}//${window.location.host}${WS_PATH}`
}

// ---------------------------------------------------------------- 模块级状态
const quotes = new Map<string, PriceQuote>()
const tickerListeners = new Map<string, Set<Listener>>()
const statusListeners = new Set<Listener>()   // 连接状态变化
const anyListeners = new Set<Listener>()      // 任意一条行情变化

let socket: WebSocket | null = null
let connected = false
let retryCount = 0
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function notifyStatus() {
  for (const listener of Array.from(statusListeners)) listener()
}

function setConnected(next: boolean) {
  if (connected === next) return
  connected = next
  notifyStatus()
}

function scheduleReconnect() {
  if (reconnectTimer !== null) return
  const delay = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * 2 ** retryCount)
  retryCount += 1
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    ensureSocket()
  }, delay)
}

function ensureSocket() {
  if (socket) {
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) return
  }
  let next: WebSocket
  try {
    next = new WebSocket(resolveStreamUrl())
  } catch {
    scheduleReconnect()
    return
  }
  socket = next

  next.onopen = () => {
    retryCount = 0
    setConnected(true)
  }
  next.onmessage = (event: MessageEvent) => {
    ingest(typeof event.data === 'string' ? event.data : '')
  }
  // onerror 之后紧跟 onclose，重连统一放在 onclose 里处理
  next.onerror = () => {}
  next.onclose = () => {
    if (socket === next) socket = null
    setConnected(false)
    scheduleReconnect()
  }
}

function ingest(raw: string) {
  if (!raw) return
  let payload: unknown
  try {
    payload = JSON.parse(raw)
  } catch {
    return
  }
  if (typeof payload !== 'object' || payload === null) return
  const items = (payload as { items?: unknown }).items
  if (!Array.isArray(items)) return

  const touched: string[] = []
  for (const item of items) {
    if (typeof item !== 'object' || item === null) continue
    const row = item as { t?: unknown; p?: unknown; c?: unknown }
    if (typeof row.t !== 'string') continue
    const price = Number(row.p)
    if (!Number.isFinite(price)) continue
    const changePctRaw = Number(row.c)
    const changePct = Number.isFinite(changePctRaw) ? changePctRaw : 0

    const prev = quotes.get(row.t)
    if (prev && prev.price === price && prev.changePct === changePct) continue
    quotes.set(row.t, { price, changePct })
    touched.push(row.t)
  }

  if (touched.length === 0) return
  for (const ticker of touched) {
    const listeners = tickerListeners.get(ticker)
    if (!listeners) continue
    for (const listener of Array.from(listeners)) listener()
  }
  for (const listener of Array.from(anyListeners)) listener()
}

function subscribeTicker(ticker: string, listener: Listener) {
  let set = tickerListeners.get(ticker)
  if (!set) {
    set = new Set()
    tickerListeners.set(ticker, set)
  }
  set.add(listener)
}

function unsubscribeTicker(ticker: string, listener: Listener) {
  const set = tickerListeners.get(ticker)
  if (!set) return
  set.delete(listener)
  if (set.size === 0) tickerListeners.delete(ticker)
}

// ---------------------------------------------------------------- Hooks

/**
 * 按 ticker 订阅单条行情。只有该 ticker 的价格变化时组件才重渲染。
 * 未收到过该 ticker 的行情时返回 null，调用方应回退到接口返回的静态值。
 */
export function usePriceQuote(ticker: string): PriceQuote | null {
  const [quote, setQuote] = useState<PriceQuote | null>(() => quotes.get(ticker) ?? null)

  useEffect(() => {
    if (!ticker) return
    const listener = () => setQuote(quotes.get(ticker) ?? null)
    listener() // 挂载时立即同步一次，避免错过首帧快照
    subscribeTicker(ticker, listener)
    ensureSocket()
    return () => unsubscribeTicker(ticker, listener)
  }, [ticker])

  return quote
}

/** 整表视角：返回全量快照 Map + 连接状态。会随任何一条行情变化而重渲染。 */
export function usePriceStream(): { prices: Map<string, PriceQuote>; connected: boolean } {
  const [, setVersion] = useState(0)

  useEffect(() => {
    const listener = () => setVersion((v) => v + 1)
    anyListeners.add(listener)
    statusListeners.add(listener)
    ensureSocket()
    return () => {
      anyListeners.delete(listener)
      statusListeners.delete(listener)
    }
  }, [])

  return { prices: new Map(quotes), connected }
}

/** 只要连接状态，不订阅行情。用于状态指示灯。 */
export function usePriceStreamStatus(): boolean {
  const [state, setState] = useState(connected)

  useEffect(() => {
    const listener = () => setState(connected)
    statusListeners.add(listener)
    ensureSocket()
    listener()
    return () => {
      statusListeners.delete(listener)
    }
  }, [])

  return state
}
