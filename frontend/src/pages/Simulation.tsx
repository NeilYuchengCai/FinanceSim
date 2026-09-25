import { useState } from 'react'

export default function Simulation() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [currentDay] = useState(0)

  return (
    <div>
      <div className="page-header">
        <h2>Simulation</h2>
        <p className="subtitle">Control the simulation clock</p>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Simulation Controls</span>
          <span className="badge badge-dot green"></span>
        </div>

        <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          <div>
            <div className="stat-value">Day {currentDay}</div>
            <div className="stat-change">Current Day</div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className="btn btn-primary"
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <button className="btn btn-secondary">Step</button>
          </div>

          <div>
            <label>Speed: </label>
            <select
              className="input-field"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            >
              <option value={1}>1x</option>
              <option value={10}>10x</option>
              <option value={100}>100x</option>
              <option value={1000}>1000x</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Market Regime</span>
          </div>
          <div className="stat-value">CALM</div>
          <div className="stat-change">Current Market State</div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Events Today</span>
          </div>
          <div className="stat-value">0</div>
          <div className="stat-change">Scheduled Events</div>
        </div>
      </div>
    </div>
  )
}
