export default function Markets() {
  return (
    <div>
      <div className="page-header">
        <h2>市场概览</h2>
        <p className="subtitle">市场概况和指数</p>
      </div>

      <div className="grid-4">
        {[
          { name: '涨幅榜', value: '+2.34%', positive: true },
          { name: '跌幅榜', value: '-1.87%', positive: false },
          { name: '活跃榜', value: '12.5M', positive: true },
          { name: 'S&P 500', value: '5,234.18', positive: true },
        ].map((index, i) => (
          <div key={i} className="card">
            <div className="stat-value">{index.value}</div>
            <div className="stat-change">{index.name}</div>
            <div className={`stat-change ${index.positive ? 'positive' : 'negative'}`}>
              {index.value.startsWith('+') || index.value.startsWith('-') ? index.value : ''}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">市场广度</span>
        </div>
        <div className="chart-container">加载中...</div>
      </div>
    </div>
  )
}
