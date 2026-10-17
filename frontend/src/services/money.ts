/**
 * 金额格式化（带真实币种换算）。
 *
 * formatCurrency 只是"按某币种符号格式化给定数字"（不换算）。
 * formatMoney 才会在展示前，把 value（币种 from）按实时 FX 汇率换算到
 * 用户在设置里选中的展示货币（getSettings().currency），再格式化。
 *
 * 因此切换展示货币时，所有用 formatMoney 的金额都会按汇率重估，而不是只换符号。
 */
import { formatCurrency, getLanguage, type CurrencyCode, type LanguageCode } from '../i18n'
import { getSettings } from '../hooks/useSettings'
import { convertCurrency } from './fxRates'

export function formatMoney(
  value: number,
  from: CurrencyCode = 'USD',
  language?: LanguageCode,
): string {
  const to = getSettings().currency
  const converted = convertCurrency(value, from, to)
  return formatCurrency(converted, to, language)
}

/** 紧凑货币格式（如 €1.08B），同样先按展示货币换算。适合市值等大额数字。 */
export function formatMoneyCompact(
  value: number,
  from: CurrencyCode = 'USD',
  language?: LanguageCode,
): string {
  const to = getSettings().currency
  const converted = convertCurrency(value, from, to)
  const lang = language || getLanguage()
  try {
    return new Intl.NumberFormat(lang === 'zh' ? 'zh-CN' : 'en-US', {
      style: 'currency',
      currency: to,
      notation: 'compact',
      maximumFractionDigits: 2,
    }).format(Number.isFinite(converted) ? converted : 0)
  } catch {
    return formatMoney(value, from, language)
  }
}
