import React, { useState } from 'react'
import SemanticMap from '../components/SemanticMap'
import ShotCompare from '../components/ShotCompare'

export default function MapScreen({ data, playful, go, runKey, replay, motion }) {
  const [showC, setShowC] = useState(true)
  const [showT, setShowT] = useState(true)
  // One slot per arm, filled by clicking a marker in that arm. The reader chooses the
  // pair: the arms fire independently, so no shot is "the same" across them.
  const [pair, setPair] = useState({ control: null, test: null })
  return (
    <div className="screen-inner">
      <div className="kicker"><span className="dot"></span> Step 02 · Where the shots landed</div>
      <div className="two-col" style={{ gridTemplateColumns: "1.25fr 0.85fr", alignItems: "start" }}>
        <div className="panel" style={{ padding: 16 }}>
          <SemanticMap data={data} showControl={showC} showTest={showT} playful={playful} runKey={runKey} motion={motion} onPick={shot => setPair(p => ({ ...p, [shot.group]: shot }))} picked={pair} />
        </div>
        <div className="stack-lg">
          <h2 className="display" style={{ fontSize: 34 }}>Two landing zones</h2>
          <p className="lede" style={{ fontSize: 16 }}>
            Each marker is one shot — where that answer settled.
            <strong> Click one in each arm to read them side by side below.</strong>
          </p>
          {data.truncatedShots > 0 && (
            <p className="rail-note" style={{ color: "var(--test)", margin: 0 }}>
              ⚠ {data.truncatedShots} of {data.N * 2} shots hit the {data.setup?.maxTokens || "token"} budget
              and stopped mid-answer — their landing zones are measured on a cut answer.
            </p>
          )}
          {/* What is selected, not what it says — the answers themselves are read in the
              full-width band under the map, which is the only place two of them fit. */}
          <div className="panel" style={{ minHeight: 116 }}>
            <div className="panel-label" style={{ marginBottom: 10 }}>Selected</div>
            {[
              { slot: pair.control, name: "CONTROL", color: "var(--control)",
                hint: "click a black shot" },
              { slot: pair.test, name: "TEST", color: "var(--test)",
                hint: "click a red shot" },
            ].map(({ slot, name, color, hint }) => (
              <div key={name} style={{
                display: "flex", alignItems: "baseline", gap: 10, padding: "6px 0",
                borderTop: "1px solid var(--line)",
              }}>
                <span className="panel-label" style={{ color, minWidth: 72 }}>{name}</span>
                <span className="rail-note" style={{ fontSize: 12, flex: 1 }}>
                  {slot
                    ? <>shot {slot.idx + 1} of {data.N}{slot.truncated ? " · ⚠ cut" : ""}</>
                    : <span style={{ opacity: 0.55 }}>◉ {hint}</span>}
                </span>
              </div>
            ))}
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
          <button className="btn btn-ghost" onClick={() => { setPair({ control: null, test: null }); replay() }} style={{ alignSelf: "flex-start" }}>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M13 8a5 5 0 1 1-1.5-3.5M13 2v3h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Replay volley
          </button>
        </div>
      </div>

      <ShotCompare
        control={pair.control}
        test={pair.test}
        maxTokens={data.setup?.maxTokens}
        onClear={() => setPair({ control: null, test: null })}
      />

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
