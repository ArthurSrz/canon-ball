import React from 'react'

export default function SetupScreen({ data, playful, go, mode, setMode, running, fire }) {
  const M = data.injectionModes
  const active = M.find(m => m.id === mode)
  return (
    <div className="screen-inner">
      <h2 className="display">Load with a prompt and a knowledge layer</h2>
      <p className="lede" style={{ marginBottom: 36, maxWidth: "56ch" }}>
        The canon will fire twice. Once without a
        <span style={{ color: "var(--gold)" }}> knowledge layer</span> <span className="control-word">(control)</span>.
        Once with a <span style={{ color: "var(--gold)" }}>knowledge layer</span> <span className="test-word">(test)</span>.
      </p>

      <div className="two-col" style={{ gridTemplateColumns: "1.1fr 0.9fr", gap: 40 }}>
        <div className="stack-lg">
          <div className="field">
            <div className="field-label">1 · The prompt</div>
            <textarea className="input" rows="2" defaultValue={data.setup.prompt}></textarea>
          </div>
          <div className="field knowledge">
            <div className="field-label" style={{ color: "var(--gold)" }}>2 · The knowledge layer</div>
            <textarea className="input" rows="4" defaultValue={data.setup.knowledgeLayer}></textarea>
          </div>
        </div>

        <div className="stack-lg">
          <div className="field">
            <div className="field-label">3 · How it's wired in</div>
            <div className="modepick">
              {M.map(m => (
                <button key={m.id} className={"modechip" + (mode === m.id ? " active" : "")} onClick={() => setMode(m.id)}>
                  <div className="mc-name">{m.name}</div>
                </button>
              ))}
            </div>
          </div>
          <p className="lede" style={{ fontSize: 14, color: "var(--ink)", margin: 0 }}>
            {active.how}
          </p>
        </div>
      </div>

      <div className="nav-row">
        <button className="btn btn-ghost" onClick={() => go(0)}>Back</button>
        <div className="nav-spacer"></div>
        <button className="btn btn-primary" disabled={running} onClick={fire}>
          {running ? "Firing…" : "Fire " + data.setup.nTrials * 2 + " shots"}
          {!running && <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3" fill="currentColor" /><path d="M8 1v3M8 12v3M1 8h3M12 8h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>}
        </button>
      </div>
    </div>
  )
}
