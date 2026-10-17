/**
 * FX 汇率服务（前端）
 *
 * 后端 /api/v1/fx/rates 返回以 USD 为基准的汇率表：rate[X] = 1 单位 X 折合多少 USD。
 * 本地据此把任意币种金额换算到用户选中的展示货币（USD 枢纽交叉汇率）。
 *
 * 换算：amount(From) → USD = amount * rate[From] → To = USD / rate[To]
 * 离线/接口不可用时 rates 退化为仅 {USD:1}，convertCurrency 返回原值（不崩溃、不误转换）。
 */
import axios from 'axios'

// rate[X] = 1 单位 X 折合多少 USD
let rates: Record<string, number> = { USD: 1 }
let loaded = false
let loadingPromise: Promise<void> | null = null

export function getRates(): Record<string, number> {
  return rates
}

export function isRatesLoaded(): boolean {
  return loaded
}

export async function loadFxRates(force = false): Promise<void> {
  if (loaded && !force) return
  if (loadingPromise) return loadingPromise
  loadingPromise = (async () => {
    try {
      const res = await axios.get('/api/v1/fx/rates', { timeout: 5000 })
      const r = res.data && res.data.rates
      if (r && typeof r === 'object') {
        rates = { USD: 1, ...r }
        loaded = true
      }
    } catch {
      // 离线或接口不可用时保留默认（仅 USD），换算退化为"不转换"
    } finally {
      loadingPromise = null
    }
  })()
  return loadingPromise
}

/** 把 amount（币种 from）换算到币种 to。USD 枢纽交叉汇率。 */
export function convertCurrency(amount: number, from: string, to: string): number {
  if (from === to) return amount
  const rf = rates[from]
  const rt = rates[to]
  if (!rf || !rt || !Number.isFinite(amount)) return amount
  const usd = amount * rf
  return usd / rt
}
