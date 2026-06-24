import React, { useState, useEffect, useMemo, useRef } from 'react'
import { getChainResults, getChainStatus, getChainDiff } from '../api'

/* ─── Borges Graph component ──────────────────────────────────────────────── */

const PAD = { t: 32, r: 24, b: 32, l: 48 }
const W = 560
const H = 340

function BorgesGraph({ graph, color, label }) {
  const [step, setStep] = useState(0)
  const [hovered, setHovered] = useState(null)

  const { clusters, maxDepth, maxCtx, steps } = useMemo(() => {
    if (!graph?.steps?.length) return { clusters: [], maxDepth: 1, maxCtx: 1, steps: [] }

    const steps = graph.steps
    const allNodes = []
    steps.forEach((s, si) => {
      const nodes = s.subgraph?.nodes || []
      nodes.forEach(n => allNodes.push({ ...n, stepIdx: si }))
    })

    const maxDepth = Math.max(1, ...allNodes.map(n => n.depth || 0))
    const maxCtx = Math.max(1, ...allNodes.map(n => n.ctx_idx || 0))

    // Build clusters: group nodes by (depth, ctx_idx) per step
    const clustersByStep = steps.map((s, si) => {
      const map = {}
      const nodes = s.subgraph?.nodes || []
      nodes.forEach(n => {
        const k = `${n.depth}:${n.ctx_idx}`
        if (!map[k]) map[k] = { depth: n.depth || 0, ctx_idx: n.ctx_idx || 0, inf: 0, count: 0, type: n.type, label: n.label || '' }
        map[k].inf += Math.abs(n.influence || 0)
        map[k].count++
      })
      return Object.values(map)
    })

    return { clusters: clustersByStep, maxDepth, maxCtx, steps }
  }, [graph])

  const cx = d => PAD.l + (d / Math.max(maxDepth, 1)) * (W - PAD.l - PAD.r)
  const cy = c => PAD.t + (c / Math.max(maxCtx, 1)) * (H - PAD.t - PAD.b)

  const currentStep = Math.min(step, steps.length - 1)
  const token = steps[currentStep]?.token || '?'

  // Static "footprint" of the whole chain (deduped by position), drawn faintly so
  // scrubbing swaps a bold per-step layer against stable context. The serial chain
  // makes per-step graphs land on similar coordinates, so a cumulative fade reads as
  // static — showing one step at a time against the footprint makes the change legible.
  const ghost = useMemo(() => {
    const m = {}
    clusters.flat().forEach(c => {
      const k = `${c.depth}:${c.ctx_idx}`
      if (!m[k] || c.inf > m[k].inf) m[k] = c
    })
    return Object.values(m)
  }, [clusters])
  const current = clusters[currentStep] || []

  function nodeColor(c) {
    if (c.type === 'embedding') return '#000'
    if (c.type === 'logit') return color  // predicted-token node uses the panel color
    return '#444'
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--display)', fontSize: 13, textTransform: 'uppercase', letterSpacing: 1, color }}>{label}</span>
        <div style={{ flex: 1 }} />
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#777' }}>
          step {currentStep + 1}/{steps.length} · {current.length} clusters · token <strong style={{ color }}>&ldquo;{token}&rdquo;</strong>
        </span>
      </div>

      <div className="graph-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
          {/* axis labels */}
          <text x={PAD.l} y={PAD.t - 10} fontFamily="var(--mono)" fontSize="9" fill="#aaa" letterSpacing="1">LAYER DEPTH →</text>
          <text x={12} y={H / 2} fontFamily="var(--mono)" fontSize="9" fill="#aaa" textAnchor="middle"
            transform={`rotate(-90 12 ${H / 2})`}>CTX POS</text>

          {/* grid */}
          {[0, 0.25, 0.5, 0.75, 1].map(t => (
            <line key={t} x1={cx(t * maxDepth)} y1={PAD.t} x2={cx(t * maxDepth)} y2={H - PAD.b}
              stroke="#e4e4e4" strokeWidth="1" />
          ))}

          {/* full-chain footprint — faint, static context */}
          {ghost.map((c, i) => (
            <circle key={`g${i}`} cx={cx(c.depth)} cy={cy(c.ctx_idx)} r={3}
              fill="none" stroke="#d8d8d8" strokeWidth="1" opacity="0.7" />
          ))}

          {/* current step — bold layer that changes as you scrub the slider */}
          {current.map((c, i) => {
            const r = Math.min(13, Math.max(4, Math.sqrt(c.inf) * 5.5))
            const col = nodeColor(c)
            const isHov = hovered === i
            return (
              <g key={i} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
                <circle cx={cx(c.depth)} cy={cy(c.ctx_idx)} r={r + 6} fill="transparent" />
                <circle cx={cx(c.depth)} cy={cy(c.ctx_idx)} r={r}
                  fill={c.type === 'logit' ? col : '#fff'}
                  stroke={col}
                  strokeWidth={c.type === 'logit' ? 2.5 : 2}
                  opacity={0.95} />
                {isHov && (
                  <text x={cx(c.depth)} y={cy(c.ctx_idx) - r - 5}
                    fontFamily="var(--mono)" fontSize="8" fill={col} textAnchor="middle">
                    {c.label ? c.label.slice(0, 24) : `L${c.depth} ctx${c.ctx_idx}`}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* step slider */}
      {steps.length > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#777', minWidth: 20 }}>0</span>
          <input type="range" min={0} max={steps.length - 1} value={currentStep}
            onChange={e => setStep(Number(e.target.value))}
            style={{ flex: 1, accentColor: color }} />
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#777', minWidth: 20 }}>{steps.length - 1}</span>
        </div>
      )}
    </div>
  )
}

/* ─── Dominance ratio bar ─────────────────────────────────────────────────── */

function DominanceBar({ graph, color }) {
  const ratios = useMemo(() => {
    if (!graph?.steps) return []
    return graph.steps.map(s => {
      const nodes = s.subgraph?.nodes || []
      const links = s.subgraph?.links || []
      if (!links.length) return null
      const total = links.reduce((sum, l) => sum + Math.abs(l.weight || 0), 0)
      const topLink = links.reduce((best, l) => Math.abs(l.weight) > Math.abs(best.weight || 0) ? l : best, links[0])
      return total > 0 ? Math.abs(topLink.weight) / total : null
    }).filter(Boolean)
  }, [graph])

  if (!ratios.length) return null

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#777', marginBottom: 6, letterSpacing: '1px' }}>
        SERIAL DOMINANCE — previous token's share of next prediction
      </div>
      <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 32 }}>
        {ratios.map((r, i) => (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <div style={{ width: '100%', background: color, height: `${r * 100}%`, opacity: 0.8 }} />
            <span style={{ fontFamily: 'var(--mono)', fontSize: 8, color: '#777' }}>{Math.round(r * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── Differential graph — control vs test, step 0 ────────────────────────── */

const STATUS_STYLE = {
  added:      { color: 'var(--gold)',    fill: 'var(--gold)', label: 'recruited by KL' },
  removed:    { color: 'var(--control)', fill: 'none',        label: 'dropped under KL' },
  amplified:  { color: 'var(--gold)',    fill: 'none',        label: 'amplified' },
  suppressed: { color: 'var(--test)',    fill: 'none',        label: 'suppressed' },
  unchanged:  { color: '#ccc',           fill: 'none',        label: 'unchanged' },
}
const STATUS_ORDER = ['added', 'removed', 'amplified', 'suppressed', 'unchanged']

// Relative influence change as a signed percentage (null for added/removed, where it's undefined).
const fmtPct = (r) => (r == null ? '' : `${r > 0 ? '+' : ''}${Math.round(r * 100)}%`)

function DiffGraph({ diff }) {
  const [hovered, setHovered] = useState(null)

  const { nodes, counts, maxDepth, maxCtx } = useMemo(() => {
    const all = diff?.nodes || []
    const feats = all.filter(n => n.type === 'cross layer transcoder' || n.feature != null)
    const maxDepth = Math.max(1, ...feats.map(n => n.depth || 0))
    const maxCtx = Math.max(1, ...feats.map(n => n.ctx_idx || 0))
    const counts = {}
    STATUS_ORDER.forEach(s => { counts[s] = 0 })
    feats.forEach(n => { counts[n.status] = (counts[n.status] || 0) + 1 })
    return { nodes: feats, counts, maxDepth, maxCtx }
  }, [diff])

  if (!nodes.length) return null

  const cx = d => PAD.l + (d / Math.max(maxDepth, 1)) * (W - PAD.l - PAD.r)
  const cy = c => PAD.t + (c / Math.max(maxCtx, 1)) * (H - PAD.t - PAD.b)

  // Draw faded/unchanged first, salient (added/removed) on top.
  const drawOrder = [...nodes].sort(
    (a, b) => STATUS_ORDER.indexOf(b.status) - STATUS_ORDER.indexOf(a.status)
  )

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--display)', fontSize: 13, textTransform: 'uppercase', letterSpacing: 1 }}>
          Differential — step 0
        </span>
        <div style={{ flex: 1 }} />
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#777' }}>
          control <strong style={{ color: 'var(--control)' }}>&ldquo;{diff.control_token}&rdquo;</strong>
          {' '}vs test <strong style={{ color: 'var(--gold)' }}>&ldquo;{diff.test_token}&rdquo;</strong>
        </span>
      </div>

      <div className="graph-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
          <text x={PAD.l} y={PAD.t - 10} fontFamily="var(--mono)" fontSize="9" fill="#aaa" letterSpacing="1">LAYER DEPTH →</text>
          <text x={12} y={H / 2} fontFamily="var(--mono)" fontSize="9" fill="#aaa" textAnchor="middle"
            transform={`rotate(-90 12 ${H / 2})`}>CTX POS</text>

          {[0, 0.25, 0.5, 0.75, 1].map(t => (
            <line key={t} x1={cx(t * maxDepth)} y1={PAD.t} x2={cx(t * maxDepth)} y2={H - PAD.b}
              stroke="#e4e4e4" strokeWidth="1" />
          ))}

          {drawOrder.map((n, i) => {
            const s = STATUS_STYLE[n.status] || STATUS_STYLE.unchanged
            const salient = n.status === 'added' || n.status === 'removed'
            const r = Math.min(11, Math.max(3, Math.sqrt(Math.abs(n.influence || 0.3)) * 6))
            const isHov = hovered === i
            return (
              <g key={i} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
                <circle cx={cx(n.depth)} cy={cy(n.ctx_idx)} r={r + 4} fill="transparent" />
                <circle cx={cx(n.depth)} cy={cy(n.ctx_idx)} r={r}
                  fill={s.fill} stroke={s.color}
                  strokeWidth={salient ? 2 : 1}
                  opacity={salient ? 0.95 : 0.3} />
                {isHov && (
                  <text x={cx(n.depth)} y={cy(n.ctx_idx) - r - 5}
                    fontFamily="var(--mono)" fontSize="8" fill={s.color} textAnchor="middle">
                    {(n.label ? n.label.slice(0, 22) : `L${n.depth} ctx${n.ctx_idx}`)} · {n.status}
                    {n.rel_influence != null ? ` ${fmtPct(n.rel_influence)}` : ''}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* legend with live counts */}
      <div className="chiprow" style={{ marginTop: 10, flexWrap: 'wrap', gap: 8 }}>
        {STATUS_ORDER.filter(s => counts[s] > 0).map(s => {
          const st = STATUS_STYLE[s]
          return (
            <span key={s} className="chip" style={{ color: st.color, borderColor: st.color, fontSize: 10 }}>
              <span style={{
                display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                background: st.fill === 'none' ? 'transparent' : st.color,
                border: `1.5px solid ${st.color}`, marginRight: 6, verticalAlign: 'middle',
              }} />
              {st.label} · {counts[s]}
            </span>
          )
        })}
      </div>
    </div>
  )
}

/* ─── FocalLineScreen ─────────────────────────────────────────────────────── */

export default function FocalLineScreen({ data, go }) {
  const [chains, setChains] = useState(null)
  const [diff, setDiff] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [chainStatus, setChainStatus] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    let interval = null

    async function poll() {
      try {
        const status = await getChainStatus()
        setChainStatus(status)

        if (status.state === 'ready') {
          const result = await getChainResults()
          setChains(result)
          // Differential is best-effort: both chains must be on disk. Never blocks the main view.
          try { setDiff(await getChainDiff()) } catch (_) { setDiff(null) }
          setLoading(false)
          clearInterval(interval)
        } else if (status.state === 'failed') {
          setError(status.error || 'Chain computation failed')
          setLoading(false)
          clearInterval(interval)
        }
        // 'computing' or 'idle' → keep polling
      } catch (e) {
        // If status endpoint not available yet, try results directly (backwards compat)
        try {
          const result = await getChainResults()
          setChains(result)
          try { setDiff(await getChainDiff()) } catch (_) { setDiff(null) }
          setLoading(false)
          clearInterval(interval)
        } catch (_) {}
      }
    }

    poll()
    interval = setInterval(poll, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="screen-inner">
      <div className="kicker"><span className="dot"></span> Step 05 · The focal line</div>
      <h2 className="display">The Borges chain</h2>
      <p className="lede" style={{ marginBottom: 24, maxWidth: '72ch' }}>
        Each token the model generates is almost entirely caused by the previous one.
        The attribution graph traces this serial chain: <strong>layer depth</strong> (X) ×{' '}
        <strong>context position</strong> (Y). Nodes sized by influence.
        Use the slider to walk the chain step by step.
      </p>

      {loading && (
        <div className="panel" style={{ padding: 40, textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--display)', fontSize: 20, textTransform: 'uppercase', marginBottom: 8 }}>
            Computing chains…
          </div>
          {chainStatus?.state === 'computing' && chainStatus.total > 0 && (
            <>
              <div style={{ margin: '16px auto', background: '#eee', height: 6, width: '80%', maxWidth: 300 }}>
                <div style={{
                  background: 'var(--gold)', height: '100%',
                  width: `${(chainStatus.step / chainStatus.total) * 100}%`,
                  transition: 'width 0.5s ease',
                }} />
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#777' }}>
                Step {chainStatus.step} of {chainStatus.total} · Circuit Tracer running
              </div>
            </>
          )}
          {(!chainStatus || chainStatus.state === 'idle') && (
            <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#777' }}>
              Fire an experiment first to generate chains.
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="panel" style={{ borderColor: 'var(--test)', padding: 24 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--test)' }}>
            Chain unavailable: {error}
          </div>
        </div>
      )}

      {chains && (
        <>
          <div className="panel" style={{ marginBottom: 24 }}>
            <div className="panel-label">Traced inputs — same as the volley</div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 12.5, lineHeight: 1.6 }}>
              <div style={{ marginBottom: 8, display: 'flex', gap: 10 }}>
                <span style={{ color: '#777', minWidth: 96, flex: 'none' }}>PROMPT</span>
                <span>{chains.control?.prompt || '—'}</span>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <span style={{ color: 'var(--gold)', minWidth: 96, flex: 'none' }}>KNOWLEDGE</span>
                <span>{chains.test?.system_prompt?.trim() || '(none)'}</span>
              </div>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#999', marginTop: 12, lineHeight: 1.5 }}>
              The exact prompt and knowledge layer from your volley. The chain feeds them to
              <strong> gemma-2-2b</strong> as <strong>knowledge + prompt</strong> (template-style
              concatenation), independent of the injection mode used on the Landing Map — so the
              <em> wiring</em> can differ even though the text is identical, and gemma-2-2b's own
              tokens won't match the experiment's gemma-3-4b-it answers.
            </div>
          </div>

          <div className="two-col" style={{ gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
            <div className="panel">
              <BorgesGraph graph={chains.control} color="var(--control)" label="Control — no KL" />
              <DominanceBar graph={chains.control} color="var(--control)" />
            </div>
            <div className="panel" style={{ borderColor: 'var(--gold)' }}>
              <BorgesGraph graph={chains.test} color="var(--gold)" label="Test — with knowledge layer" />
              <DominanceBar graph={chains.test} color="var(--gold)" />
            </div>
          </div>

          {diff && (
            <div className="panel" style={{ borderColor: 'var(--gold)', borderStyle: 'dashed', marginBottom: 24 }}>
              <DiffGraph diff={diff} />
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#999', marginTop: 10, lineHeight: 1.5 }}>
                Step 0 only — the single token where both chains share input context.
                <strong style={{ color: 'var(--gold)' }}> Recruited</strong> features are circuits the
                knowledge layer switched on that the control never used; <strong>dropped</strong> ones it
                switched off. Shared circuits are <strong style={{ color: 'var(--gold)' }}>amplified</strong> or
                <strong style={{ color: 'var(--test)' }}> suppressed</strong> when the knowledge layer shifts
                their influence by ≥10% relative to control (hover a node for the exact %).
              </div>
            </div>
          )}

          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#999', margin: '4px 0 16px', borderLeft: '3px solid #e4e4e4', paddingLeft: 12, lineHeight: 1.6 }}>
            The chains above trace <strong>gemma-2-2b</strong> via Neuronpedia Circuit Tracer —
            an independent model run on the same prompt, not a trace of the experiment outputs on the Landing Map.
            The Library of Babel is consulted in series.
          </div>

          {chains.control?.meta?.attribution_url && (
            <div className="chiprow" style={{ marginBottom: 8 }}>
              <a href={chains.control.meta?.attribution_url} target="_blank" rel="noopener"
                className="chip" style={{ color: 'var(--link)', borderColor: 'var(--link)' }}>
                ↗ View control graph on Neuronpedia
              </a>
              {chains.test?.meta?.attribution_url && (
                <a href={chains.test.meta?.attribution_url} target="_blank" rel="noopener"
                  className="chip" style={{ color: 'var(--link)', borderColor: 'var(--link)' }}>
                  ↗ View test graph on Neuronpedia
                </a>
              )}
            </div>
          )}
        </>
      )}

      <div className="nav-row">
        <button className="btn btn-ghost" onClick={() => go(4)}>Back</button>
        <div className="nav-spacer"></div>
        <button className="btn btn-primary" onClick={() => go(0)}>
          Run again
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
            <path d="M13 8a5 5 0 1 1-1.5-3.5M13 2v3h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  )
}
