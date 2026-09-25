export default function Equities() {
  return (
    <div>
      <div className="page-header">
        <h2>Equities</h2>
        <p className="subtitle">Stock market overview and trading</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Market Summary</span>
          <span className="tag tag-blue">SIMULATION</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Price</th>
              <th>Change</th>
              <th>Volume</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={5} className="loading">Loading market data...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
