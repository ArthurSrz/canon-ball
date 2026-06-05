import React, { useState } from 'react'
import SemanticMap from '../components/SemanticMap'

export default function MapScreen({ data, playful, go, runKey, replay, motion }) {
  const [showC, setShowC] = useState(true)
  const [showT, setShowT] = useState(true)
  const [picked, setPicked] = useState(null)
  return (
    <div className="screen-inner">
      <div className="kicker"><span className="dot"></span> Step 02 · Where the shots landed</div>
      <div className="two-col" style={{ gridTemplateColumns: "1.25fr 0.85fr", alignItems: "start" }}>
        <div className="panel" style={{ padding: 16 }}>
          <SemanticMap data={data} showControl={showC} showTest={showT} playful={playful} runKey={runKey} motion={motion} onPick={setPicked} picked={picked} />
        </div>
        <div className="stack-lg">
          <h2 className="display" style={{ fontSize: 34 }}>Two landing zones</h2>
          <p className="lede" style={{ fontSize: 16 }}>
            Each marker is one shot — where that answer settled.
            <strong> Click any shot to read what the model actually said.</strong>
          </p>
          <div className="panel" style={{ borderColor: picked ? picked.warm ? "var(--test)" : "var(--control)" : "var(--line)", transition: "border-color .2s", minHeight: 116 }}>
            {picked ? (
              <div>
                <div className="panel-label" style={{ color: picked.warm ? "var(--test)" : "var(--control)" }}>
                  {picked.warm ? "TEST" : "CONTROL"} · shot {picked.i + 1} of {data.N}
                </div>
                <p style={{ fontFamily: "var(--display)", fontSize: 21, lineHeight: 1.35, margin: 0 }}>
                  "{picked.output}"
                </p>
              </div>
            ) : (
              <div style={{ display: "grid", placeItems: "center", minHeight: 92, textAlign: "center" }}>
                <span className="rail-note" style={{ fontSize: 12 }}>◉ click a landed shot<br />to read its answer</span>
              </div>
            )}
          </div>
          <div className="panel">
            <label className="legend" style={{ cursor: "pointer", marginBottom: 12 }}>
              <input type="checkbox" checked={showC} onChange={e => setShowC(e.target.checked)} style={{ accentColor: "var(--control)" }} />
              <span className="lg"><span className="sw c"></span> Control — no knowledge</span>
            </label>
            <label className="legend" style={{ cursor: "pointer" }}>
              <input type="checkbox" checked={showT} onChange={e => setShowT(e.target.checked)} style={{ accentColor: "var(--test)" }} />
              <span className="lg"><span className="sw t"></span> Test — with knowledge</span>
            </label>
          </div>
          <p className="lede" style={{ fontSize: 14 }}>
            The <span className="control-word">control</span> answers sprawl across framings.
            The <span className="test-word">test</span> answers cluster on one idea — and sit
            somewhere new. The dashed arrow is the <span style={{ color: "var(--gold)" }}>steer</span>.
          </p>
          <button className="btn btn-ghost" onClick={() => { setPicked(null); replay() }} style={{ alignSelf: "flex-start" }}>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M13 8a5 5 0 1 1-1.5-3.5M13 2v3h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Replay volley
          </button>
        </div>
      </div>
      <div className="nav-row">
        <button className="btn btn-ghost" onClick={() => go(1)}>Back</button>
        <div className="nav-spacer"></div>
        <button className="btn btn-primary" onClick={() => go(3)}>
          Read the measurements
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      </div>
    </div>
  )
}
