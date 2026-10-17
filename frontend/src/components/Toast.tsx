import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { t } from '../i18n'

/**
 * 全局 Toast 机制（Wave 1）
 *
 * - 统一替代原先散落各页的自制提示（Settings 保存卡 / WorldCreator notice / Orders 底部错误）
 * - 3 秒自动消失，可点击手动关闭
 * - 右上角悬浮，深色主题：全部使用 index.css 的 CSS 变量，不写死浅色
 */

export type ToastVariant = 'success' | 'error'

interface ToastItem {
  id: number
  variant: ToastVariant
  message: string
}

interface ToastContextValue {
  success: (message: string) => void
  error: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TOAST_DURATION_MS = 3000

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const nextIdRef = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.filter((item) => item.id !== id))
  }, [])

  const push = useCallback(
    (variant: ToastVariant, message: string) => {
      const id = nextIdRef.current++
      setToasts((list) => [...list, { id, variant, message }])
      window.setTimeout(() => dismiss(id), TOAST_DURATION_MS)
    },
    [dismiss],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      success: (message: string) => push('success', message),
      error: (message: string) => push('error', message),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-container" aria-live="polite">
        {toasts.map((item) => (
          <div
            key={item.id}
            className={`toast toast-${item.variant}`}
            role="status"
            onClick={() => dismiss(item.id)}
            title={t('toast.dismiss')}
          >
            <span className="toast-icon">{item.variant === 'success' ? '✅' : '⚠️'}</span>
            <span className="toast-message">{item.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

/** 在 ToastProvider 内部使用；提供 success/error 两个入口。 */
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}
