export default function Settings() {
  return (
    <div>
      <div className="page-header">
        <h2>Settings</h2>
        <p className="subtitle">Configure your simulation</p>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">General Settings</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label>Theme</label>
            <select className="input-field">
              <option>Dark</option>
              <option>Light</option>
            </select>
          </div>
          <div>
            <label>Language</label>
            <select className="input-field">
              <option>English</option>
              <option>中文</option>
            </select>
          </div>
          <div>
            <label>Currency Display</label>
            <select className="input-field">
              <option>USD ($)</option>
              <option>EUR (€)</option>
              <option>GBP (£)</option>
            </select>
          </div>
        </div>
      </div>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">Simulation Settings</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label>Default Speed</label>
            <select className="input-field">
              <option>1x</option>
              <option>10x</option>
              <option>100x</option>
              <option>1000x</option>
            </select>
          </div>
          <div>
            <label>Data Source</label>
            <select className="input-field">
              <option>Fallback Dataset</option>
              <option>Alpha Vantage</option>
              <option>FRED</option>
              <option>Frankfurter</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
