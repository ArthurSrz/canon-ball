import React, { useEffect, useState } from 'react'
import { previewStructure } from '../api'
import KnowledgeGraphView from '../components/KnowledgeGraphView'

const CONTROL_ARMS = [
  { id: "none", name: "Nothing", how: "The control arm fires bare — the classic knowledge-vs-nothing volley." },
  { id: "prose", name: "The same facts, in prose", how: "Both arms carry the same facts. Only the form differs, so the delta is the structure effect." },
]

function LayerPreview({ title, color, body, empty }) {
  return (
    <div style={{ border: "1.5px solid var(--line-strong, #333)", padding: "10px 12px", minHeight: 96 }}>
      <div className="field-label" style={{ color, marginBottom: 6 }}>{title}</div>
      <pre style={{
        margin: 0, fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.5,
        whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 180, overflowY: "auto",
        opacity: body ? 1 : 0.45,
      }}>{body || empty}</pre>
    </div>
  )
}

export default function SetupScreen({ data, playful, go, mode, setMode, running, fire,
                                      knowledgeForm, controlForm, setControlForm }) {
  const M = data.injectionModes
  const F = data.structureForms
  const active = M.find(m => m.id === mode)
  const activeForm = F.find(f => f.id === knowledgeForm)
  const activeArm = CONTROL_ARMS.find(a => a.id === controlForm)

  const [knowledge, setKnowledge] = useState(data.setup.knowledgeLayer)
  const [preview, setPreview] = useState(null)
  const [previewError, setPreviewError] = useState(null)

  // The structurer runs server-side, and for the graph form it fires two LLM passes.
  // A short debounce would bill a frontier call per keystroke, so this one is long.
  useEffect(() => {
    const id = setTimeout(async () => {
      try {
        setPreview(await previewStructure({ knowledgeLayer: knowledge, form: knowledgeForm }))
        setPreviewError(null)
      } catch (err) {
        setPreviewError(err.message)
      }
    }, 1200)
    return () => clearTimeout(id)
  }, [knowledge, knowledgeForm])

  const renderOf = id => preview?.forms?.find(f => f.id === id)?.rendered || ""
  const stats = preview?.stats
  const graph = preview?.graph
  const graphStats = stats?.graph

  return (
    <div className="screen-inner">
      <h2 className="display">Load with a prompt and a knowledge layer</h2>
      <p className="lede" style={{ marginBottom: 36, maxWidth: "62ch" }}>
        The canon fires twice from the same <span style={{ color: "var(--gold)" }}>facts</span>.
        {controlForm === "none"
          ? <> Once with no <span style={{ color: "var(--gold)" }}>knowledge layer</span> <span className="control-word">(control)</span>, once with it <span className="test-word">(test)</span>.</>
          : <> Once with them in <span className="control-word">prose (control)</span>, once as a <span className="test-word">knowledge graph (test)</span> — so whatever moves is the structure, not the content.</>}
      </p>

      <div className="two-col" style={{ gridTemplateColumns: "1.1fr 0.9fr", gap: 40 }}>
        <div className="stack-lg">
          <div className="field">
            <div className="field-label">1 · The prompt</div>
            <textarea className="input" rows="2" defaultValue={data.setup.prompt}></textarea>
          </div>
          <div className="field knowledge">
            <div className="field-label" style={{ color: "var(--gold)" }}>2 · The knowledge, in prose</div>
            <textarea className="input" rows="5" value={knowledge}
              onChange={e => setKnowledge(e.target.value)}></textarea>
            <div className="rail-note" style={{ marginTop: 6 }}>
              {previewError
                ? `Structurer unavailable — ${previewError}`
                : stats
                  ? `${stats.n_claims} claims · subject “${stats.subject || "—"}” · ` +
                    `${Object.entries(stats.relations).map(([r, n]) => `${r} ×${n}`).join(", ")}` +
                    `${knowledgeForm === "knowledge_graph"
                        ? " · taxonomy only — the sentences are not carried"
                        : stats.claims_preserved ? "" : " · ⚠ wording altered"}`
                  : "Reading the claims…"}
            </div>
          </div>

          <div className="field">
            <div className="field-label">3 · What the structurer loads</div>
            <div className="two-col" style={{ gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <LayerPreview
                title="Control arm"
                color="var(--control)"
                body={controlForm === "none" ? "" : renderOf(controlForm)}
                empty="(fires bare — no knowledge)"
              />
              <LayerPreview
                title="Test arm"
                color="var(--test)"
                body={renderOf(knowledgeForm)}
                empty="(nothing to structure yet)"
              />
            </div>
          </div>
        </div>

        <div className="stack-lg">
          <div className="field">
            <div className="field-label" style={{ color: "var(--test)" }}>4 · The test arm's form</div>
            <div style={{ border: "1.5px solid var(--test)", padding: "10px 12px" }}>
              <div className="mc-name">{activeForm?.name || "Knowledge graph"}</div>
              <div className="rail-note" style={{ marginTop: 6 }}>
                {graph
                  ? `${graph.nodes.length} concepts · ${graph.edges.length} edges · ` +
                    `${Object.entries(graphStats?.relations || {})
                        .map(([r, n]) => `${r} ×${n}`).join(", ")}`
                  : "Reading the prose into a taxonomy…"}
              </div>
              {graph && (
                <div className="rail-note" style={{ marginTop: 4, opacity: 0.7 }}>
                  {graph.source === "llm"
                    ? `extracted by ${graph.model}`
                    : "read by rule — the LLM extractor did not run"}
                </div>
              )}
              {graph && graph.source !== "llm" && graph.fallbackReason && (
                <div className="rail-note" style={{ marginTop: 4, color: "var(--test)" }}>
                  ↳ {graph.fallbackReason}
                </div>
              )}
            </div>
          </div>
          <p className="lede" style={{ fontSize: 14, color: "var(--ink)", margin: 0 }}>
            {activeForm?.how}
          </p>

          <div className="field">
            <div className="field-label" style={{ color: "var(--control)" }}>5 · What the control arm gets</div>
            <div className="modepick">
              {CONTROL_ARMS.map(a => (
                <button key={a.id} className={"modechip" + (controlForm === a.id ? " active" : "")}
                  onClick={() => setControlForm(a.id)}>
                  <div className="mc-name">{a.name}</div>
                </button>
              ))}
            </div>
          </div>
          <p className="lede" style={{ fontSize: 14, color: "var(--ink)", margin: 0 }}>
            {activeArm?.how}
          </p>

          <div className="field">
            <div className="field-label">6 · How it's wired in</div>
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

      <div className="field" style={{ marginTop: 36 }}>
        <div className="field-label" style={{ color: "var(--test)" }}>
          The graph the test arm is loaded with
        </div>
        <KnowledgeGraphView graph={graph} claims={preview?.claims || []} />
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
