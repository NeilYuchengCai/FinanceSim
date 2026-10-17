import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** 出错时显示的区域标题，便于定位是哪个区块崩了 */
  label?: string
}

interface State {
  error: Error | null
}

/**
 * 渲染错误边界（P1-17 之后补的兜底）。
 *
 * 之前任何页面/组件渲染期抛错都会变成静默白屏，用户只能看到“打不开”却没有任何信息，
 * 排错极困难。这里把错误信息和堆栈直接渲染到屏幕上，便于定位真实崩因。
 *
 * 用法：包裹 <Routes> 或单个高风险组件（如图表）。
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: unknown) {
    // 同时打到 console，方便开发者工具里看完整堆栈
    console.error('[ErrorBoundary]', this.props.label ?? '', error, info)
  }

  handleReset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      const err = this.state.error
      return (
        <div
          style={{
            margin: 16,
            padding: 20,
            border: '1px solid var(--accent-red, #ef4444)',
            borderRadius: 8,
            background: 'var(--bg-tertiary, #1f2937)',
            color: 'var(--text-primary, #e5e7eb)',
            fontFamily: 'monospace',
            fontSize: 13,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 8, color: '#ef4444' }}>
            ⚠️ 渲染出错{this.props.label ? `（${this.props.label}）` : ''}
          </div>
          <div style={{ marginBottom: 8 }}>{err.message}</div>
          <div style={{ opacity: 0.7, fontSize: 12, maxHeight: 240, overflow: 'auto' }}>
            {err.stack}
          </div>
          <button className="btn btn-sm" style={{ marginTop: 12 }} onClick={this.handleReset}>
            重试
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
