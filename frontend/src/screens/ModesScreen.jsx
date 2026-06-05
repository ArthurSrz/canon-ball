import React from 'react'

/* ── mini zone thumbnail ── */
function ZoneThumb({ ratio, size = 48 }) {
  const r = size / 2
  const controlR = r * 0.7
  const testR = controlR * ratio
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={r * 0.85} cy={r * 1.1} r={controlR} fill="none" stroke="var(--control)" strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
      <circle cx={r * 1.15} cy={r * 0.9} r={testR} fill="none" stroke="var(--test)" strokeWidth="1.5" />
      <circle cx={r * 0.85} cy={r * 1.1} r="2" fill="var(--control)" />
      <circle cx={r * 1.15} cy={r * 0.9} r="2" fill="var(--test)" />
      <line x1={r * 0.85} y1={r * 1.1} x2={r * 1.15} y2={r * 0.9} stroke="var(--gold)" strokeWidth="0.8" strokeDasharray="2 1" />
    </svg>
  )
}

export default function ModesScreen({ data, go }) {
  const M = data.injectionModes
  return (
    <div className="screen-inner">
      <div className="kicker"><span className="dot"></span> Step 04 · How the wiring matters</div>
      <h2 className="display" style={{ marginBottom: 8 }}>Four ways to inject knowledge</h2>
      <p className="lede" style={{ maxWidth: "58ch", marginBottom: 36 }}>
        The same knowledge, the same prompt — but the delivery channel changes the
        focusing and steering effect dramatically.
      </p>

      <div className="modes-table">
        <div className="modes-header">
          <div className="modes-cell modes-rank">#</div>
          <div className="modes-cell modes-viz"></div>
          <div className="modes-cell modes-name">Mode</div>
          <div className="modes-cell modes-num">Ratio</div>
          <div className="modes-cell modes-num">Tightening</div>
          <div className="modes-cell modes-num">Shift</div>
          <div className="modes-cell modes-num">p-value</div>
        </div>
        {M.map(m => (
          <div key={m.id} className={"modes-row" + (m.rank === 1 ? " modes-best" : "") + (m.pVal >= 0.05 ? " modes-ns" : "")}>
            <div className="modes-cell modes-rank">{m.rank}</div>
            <div className="modes-cell modes-viz"><ZoneThumb ratio={m.ratio} /></div>
            <div className="modes-cell modes-name">
              <div className="modes-mode-name">{m.name}</div>
              <div className="modes-mode-how">{m.how}</div>
            </div>
            <div className="modes-cell modes-num">
              <span className="modes-big">{m.ratio.toFixed(3)}</span>
            </div>
            <div className="modes-cell modes-num">
              <span className="modes-big">{m.tighten.toFixed(1)}%</span>
            </div>
            <div className="modes-cell modes-num">
              <span className="modes-big">{m.shift.toFixed(3)}</span>
            </div>
            <div className="modes-cell modes-num">
              <span className={"modes-big" + (m.pVal < 0.05 ? " modes-sig" : " modes-nonsig")}>{m.p}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="two-col" style={{ gridTemplateColumns: "1fr 1fr", gap: 32, marginTop: 36 }}>
        {M.filter(m => m.rank <= 2).map(m => (
          <div className="panel" key={m.id}>
            <div className="panel-label">{m.name}</div>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{m.why}</p>
          </div>
        ))}
      </div>

      <div className="nav-row" style={{ marginTop: 40 }}>
        <button className="btn btn-ghost" onClick={() => go(3)}>Back</button>
        <div className="nav-spacer"></div>
        <button className="btn btn-primary" onClick={() => go(5)}>
          See the focal line
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      </div>
    </div>
  )
}
