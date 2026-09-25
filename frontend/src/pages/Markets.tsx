export default function Markets() {
  return (
    <div>
      <div className="page-header">
        <h2>Markets</h2>
        <p className="subtitle">Market overview and indices</p>
      </div>
      
      <div className="grid-4">
        {[
          { name: 'S&P 500', value: '5,234.18', change: '+0.45%', positive: true },
          { name: 'NASDAQ', value: '16,399.52', change: '+0.78%', positive: true },
          { name: 'DOW', value: '39,127.12', change: '+0.32%', positive: true },
          { name: 'Russell 2000', value: '2,089.56', change: '-0.15%', positive: false },
        ].map(index => (
          <div key={index.name} className="card">
            <div className="stat-value">{index.value}</div>
            <div className="stat-change">{index.name}</div>
            <div className={`stat-change ${index.positive ? 'positive' : 'negative'}`}>
              {index.change}
            </div>
          </div>
        ))}
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">Market Breadth</span>
        </div>
        <div className="chart-container">Market breadth chart will appear here</div>
      </div>
    </div>
  )
}
