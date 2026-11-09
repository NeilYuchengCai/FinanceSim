import { useState } from 'react'
import axios from 'axios'
import { t } from '../i18n'
import { useToast } from './Toast'

/**
 * 共享下单表单（Wave 2 从 Orders.tsx 抽取，Orders 页与资产详情页复用）
 *
 * 契约：POST /api/v1/trading/orders?world_id={worldId}
 * body: { asset_ticker, side, type, quantity, price?, stop_price? }
 */

export interface OrderFormAsset {
  ticker: string
  name?: string
}

interface OrderFormProps {
  worldId: number
  /** 固定 ticker（资产详情页传入；订单页不传则显示可编辑输入框） */
  fixedTicker?: string
  /** 资产联想列表（订单页传入 /assets 结果；不传则不校验存在性） */
  assets?: OrderFormAsset[]
  /** 提交成功后的回调（刷新列表/详情） */
  onSubmitted?: (orderId?: string) => void
}

const SIDES = ['BUY', 'SELL'] as const
const TYPES = ['MARKET', 'LIMIT'] as const

export default function OrderForm({
  worldId,
  fixedTicker,
  assets,
  onSubmitted,
}: OrderFormProps) {
  const toast = useToast()
  const [ticker, setTicker] = useState(fixedTicker ?? 'AAPL')
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY')
  const [type, setType] = useState<'MARKET' | 'LIMIT'>('MARKET')
  const [quantity, setQuantity] = useState(100)
  const [price, setPrice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const currentTicker = fixedTicker ?? ticker

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const tk = currentTicker.trim().toUpperCase()
    if (!tk) {
      setError(t('orders.tickerRequired'))
      return
    }
    // 传入资产列表时校验存在性，无效给内联红字提示
    if (assets && assets.length > 0 && !assets.some((a) => a.ticker.toUpperCase() === tk)) {
      setError(`${t('orders.tickerNotFound')}: ${tk}`)
      return
    }
    if (!Number.isFinite(quantity) || quantity < 1) {
      setError(t('orders.invalidQuantity'))
      return
    }
    if (type === 'LIMIT') {
      const limitPrice = parseFloat(price)
      if (!Number.isFinite(limitPrice) || limitPrice <= 0) {
        setError(t('orders.invalidPrice'))
        return
      }
    }

    setSubmitting(true)
    try {
      const res = await axios.post(`/api/v1/trading/orders?world_id=${worldId}`, {
        asset_ticker: tk,
        side,
        type,
        quantity,
        price: type === 'LIMIT' ? parseFloat(price) : undefined,
      })
      toast.success(t('toast.orderSubmitted'))
      onSubmitted?.(res.data?.id)
    } catch (err: any) {
      // 把后端返回的具体错误（如"市场休市，市价单不可提交"）透传给用户，
      // 而不是只显示一句笼统的失败提示。
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        t('common.error')
      setError(detail)
      toast.error(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {!fixedTicker && (
        <div style={{ marginBottom: 12 }}>
          <label>{t('equities.ticker')}</label>
          <input
            type="text"
            className="input-field"
            list="order-form-ticker-options"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="AAPL"
          />
          {assets && assets.length > 0 && (
            <datalist id="order-form-ticker-options">
              {assets.map((a) => (
                <option key={a.ticker} value={a.ticker}>
                  {a.name ?? a.ticker}
                </option>
              ))}
            </datalist>
          )}
        </div>
      )}
      <div style={{ marginBottom: 12 }}>
        <label>{t('orders.side')}</label>
        <select
          className="input-field"
          value={side}
          onChange={(e) => setSide(e.target.value as 'BUY' | 'SELL')}
        >
          {SIDES.map((s) => (
            <option key={s} value={s}>
              {s === 'BUY' ? t('orders.buy') : t('orders.sell')}
            </option>
          ))}
        </select>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>{t('orders.orderType')}</label>
        <select
          className="input-field"
          value={type}
          onChange={(e) => setType(e.target.value as 'MARKET' | 'LIMIT')}
        >
          {TYPES.map((tp) => (
            <option key={tp} value={tp}>
              {tp === 'MARKET' ? t('orders.market') : t('orders.limit')}
            </option>
          ))}
        </select>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>{t('orders.quantity')}</label>
        <input
          type="number"
          className="input-field"
          value={quantity}
          onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
          min={1}
        />
      </div>
      {type === 'LIMIT' && (
        <div style={{ marginBottom: 12 }}>
          <label>{t('orders.limitPrice')}</label>
          <input
            type="number"
            className="input-field"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="100.00"
            step="0.01"
          />
        </div>
      )}
      <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
        {submitting ? t('orders.submitting') : t('orders.submit')}
      </button>
      {error && (
        <div className="error" style={{ padding: 12, marginTop: 12, color: 'var(--accent-red)' }}>
          {error}
        </div>
      )}
    </form>
  )
}
