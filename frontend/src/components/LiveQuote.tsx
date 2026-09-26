import { useEffect, useRef, useState } from 'react'
import { usePriceQuote } from '../hooks/usePriceStream'

/**
 * 实时价格单元格。
 *
 * - 按 ticker 粒度订阅行情，只有自己变化时重渲染，不会牵动整行/整表，
 *   因此不会出现闪烁或滚动跳动。
 * - 数值变化时加一次性的高亮类（涨绿 / 跌红），600ms 后由 CSS animation 淡出。
 *   用递增的 key 让动画重新触发，比 setTimeout 反复 setState 更稳，不会抖。
 * - 未连上流 / 该 ticker 尚无行情时回退到接口返回的值；断线时保留最后已知价格。
 */

type Flash = { dir: 'up' | 'down'; seq: number } | null

function useFlashOnChange(value: number | null): Flash {
  const prev = useRef<number | null>(null)
  const seq = useRef(0)
  const [flash, setFlash] = useState<Flash>(null)

  useEffect(() => {
    if (value === null || !Number.isFinite(value)) return
    const before = prev.current
    prev.current = value
    if (before === null || before === value) return
    seq.current += 1
    setFlash({ dir: value > before ? 'up' : 'down', seq: seq.current })
  }, [value])

  return flash
}

function flashClass(flash: Flash): string {
  if (!flash) return ''
  return flash.dir === 'up' ? 'price-flash-up-fast' : 'price-flash-down-fast'
}

function flashKey(flash: Flash): string {
  return flash ? `f${flash.seq}` : 'init'
}

export interface LiveQuoteProps {
  ticker: string
  /** 流数据缺失时的兜底值（REST 接口返回的静态值） */
  fallback: number | null
  /** 自定义格式化，默认保留 2 位小数 */
  format?: (value: number) => string
}

export function LivePrice({ ticker, fallback, format }: LiveQuoteProps) {
  const quote = usePriceQuote(ticker)
  const value = quote ? quote.price : fallback
  const flash = useFlashOnChange(value)

  if (value === null || !Number.isFinite(value)) return <span>--</span>
  return (
    <span key={flashKey(flash)} className={flashClass(flash)}>
      {format ? format(value) : value.toFixed(2)}
    </span>
  )
}

export function LiveChange({ ticker, fallback, format }: LiveQuoteProps) {
  const quote = usePriceQuote(ticker)
  const value = quote ? quote.changePct : fallback
  const flash = useFlashOnChange(value)

  if (value === null || !Number.isFinite(value)) return <span>--</span>
  // 项目约定：positive=绿=涨，negative=红=跌
  const dir = value >= 0 ? 'positive' : 'negative'
  return (
    <span key={flashKey(flash)} className={`${flashClass(flash)} ${dir}`.trim()}>
      {format ? format(value) : `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`}
    </span>
  )
}
