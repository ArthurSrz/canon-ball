import React, { useState, useMemo } from 'react'

/* ═══════════════════════════════════════════════════════════
   FocalLine — convergent/divergent rays with focal point
   ═══════════════════════════════════════════════════════════ */

const W = 720
const H = 420
const FOCAL_X = W * 0.5
const INPUT_X = 40
const OUTPUT_X = W - 40
const INPUT_ZONE = { x: INPUT_X, top: 40, bottom: H - 40 }
const OUTPUT_ZONE = { x: OUTPUT_X, top: 60, bottom: H - 60 }

function lerp(a, b, t) { return a + (b - a) * t }

function distributeY(items, top, bottom) {
  if (items.length === 1) return [lerp(top, bottom, 0.5)]
  return items.map((_, i) => lerp(top, bottom, i / (items.length - 1)))
}

function FocalLine({ focal, hoveredNode, setHoveredNode }) {
  const { inputs, converge, focus, diverge } = focal

  const inputYs = useMemo(() => distributeY(inputs, INPUT_ZONE.top, INPUT_ZONE.bottom), [inputs])
  const convergeYs = useMemo(() => distributeY(converge, 60, H - 60), [converge])
  const divergeYs = useMemo(() => distributeY(diverge, OUTPUT_ZONE.top, OUTPUT_ZONE.bottom), [diverge])

  const convergeX = FOCAL_X - 80
  const divergeX = FOCAL_X + 80

  // Build edges: inputs -> converge nodes
  const convergeEdges = useMemo(() => {
    const edges = []
    converge.forEach((node, ci) => {
      node.from.forEach(srcId => {
        const si = inputs.findIndex(inp => inp.id === srcId || inp.label === srcId)
        if (si >= 0) {
          edges.push({ x1: INPUT_X + 90, y1: inputYs[si], x2: convergeX, y2: convergeYs[ci], w: node.w, hot: node.hot, gold: node.gold, srcId, nodeId: node.id })
        }
      })
    })
    return edges
  }, [inputs, converge, inputYs, convergeYs, convergeX])

  // Diverge edges: focal -> diverge nodes
  const divergeEdges = useMemo(() =>
    diverge.map((d, i) => ({
      x1: FOCAL_X + 14, y1: H / 2, x2: divergeX, y2: divergeYs[i], id: d.id
    })),
    [diverge, divergeYs, divergeX]
  )

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", overflow: "visible" }}>
      <defs>
        <marker id="arrow-gold" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6" fill="var(--gold)" />
        </marker>
      </defs>

      {/* Convergent rays: inputs -> converge nodes */}
      {convergeEdges.map((e, i) => {
        const highlighted = hoveredNode === e.nodeId || hoveredNode === e.srcId
        return (
          <path key={`ce-${i}`}
            d={`M${e.x1},${e.y1} C${lerp(e.x1, e.x2, 0.5)},${e.y1} ${lerp(e.x1, e.x2, 0.5)},${e.y2} ${e.x2},${e.y2}`}
            fill="none"
            stroke={e.gold ? "var(--gold)" : e.hot ? "var(--test)" : "var(--ink)"}
            strokeWidth={highlighted ? 2.5 : 1.2}
            opacity={hoveredNode && !highlighted ? 0.15 : e.w}
          />
        )
      })}

      {/* Converge -> focal */}
      {converge.map((node, ci) => {
        const highlighted = hoveredNode === node.id
        return (
          <path key={`cf-${ci}`}
            d={`M${convergeX + 60},${convergeYs[ci]} L${FOCAL_X - 14},${H / 2}`}
            fill="none"
            stroke={node.gold ? "var(--gold)" : node.hot ? "var(--test)" : "var(--ink)"}
            strokeWidth={highlighted ? 2.5 : 1}
            opacity={hoveredNode && !highlighted ? 0.15 : node.w * 0.7}
          />
        )
      })}

      {/* Divergent rays: focal -> output tokens */}
      {divergeEdges.map((e, i) => {
        const highlighted = hoveredNode === e.id
        return (
          <line key={`de-${i}`}
            x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
            stroke="var(--test)"
            strokeWidth={highlighted ? 2.5 : 1}
            opacity={hoveredNode && !highlighted ? 0.15 : 0.6}
            strokeDasharray="4 3"
          />
        )
      })}

      {/* Input labels */}
      {inputs.map((inp, i) => (
        <g key={`in-${inp.id}`}
          onMouseEnter={() => setHoveredNode(inp.id)}
          onMouseLeave={() => setHoveredNode(null)}
          style={{ cursor: "pointer" }}
        >
          <rect x={INPUT_X} y={inputYs[i] - 12} width={88} height={24} rx={4}
            fill={inp.kind === "know" ? "var(--gold)" : "var(--bg)"}
            stroke={inp.kind === "know" ? "var(--gold)" : "var(--line)"}
            strokeWidth="1"
            opacity={inp.kind === "know" ? 0.15 : 1}
          />
          <text x={INPUT_X + 44} y={inputYs[i] + 4} textAnchor="middle"
            fontSize="11" fontFamily="var(--mono)" fill={inp.kind === "know" ? "var(--gold)" : "var(--ink)"}>
            {inp.label}
          </text>
        </g>
      ))}

      {/* Converge nodes */}
      {converge.map((node, ci) => {
        const highlighted = hoveredNode === node.id
        return (
          <g key={`cn-${node.id}`}
            onMouseEnter={() => setHoveredNode(node.id)}
            onMouseLeave={() => setHoveredNode(null)}
            style={{ cursor: "pointer" }}
          >
            <rect x={convergeX} y={convergeYs[ci] - 12} width={120} height={24} rx={4}
              fill={highlighted ? (node.gold ? "var(--gold)" : node.hot ? "var(--test)" : "var(--ink)") : "var(--bg)"}
              stroke={node.gold ? "var(--gold)" : node.hot ? "var(--test)" : "var(--line)"}
              strokeWidth={highlighted ? 2 : 1}
              opacity={hoveredNode && !highlighted ? 0.3 : 1}
            />
            <text x={convergeX + 60} y={convergeYs[ci] + 4} textAnchor="middle"
              fontSize="10" fontFamily="var(--mono)"
              fill={highlighted ? "var(--bg)" : node.gold ? "var(--gold)" : node.hot ? "var(--test)" : "var(--ink)"}>
              {node.label.length > 18 ? node.label.slice(0, 18) + "..." : node.label}
            </text>
          </g>
        )
      })}

      {/* Focal point */}
      <circle cx={FOCAL_X} cy={H / 2} r={14}
        fill="var(--test)" stroke="var(--bg)" strokeWidth="3"
        style={{ filter: "drop-shadow(0 0 8px var(--test-glow))" }}
      />
      <text x={FOCAL_X} y={H / 2 + 4} textAnchor="middle"
        fontSize="10" fontWeight="700" fill="var(--bg)" fontFamily="var(--mono)">
        {focus.label}
      </text>
      <text x={FOCAL_X} y={H / 2 + 30} textAnchor="middle"
        fontSize="10" fill="var(--muted)" fontFamily="var(--mono)">
        p={focus.p}
      </text>

      {/* Diverge output tokens */}
      {diverge.map((d, i) => {
        const highlighted = hoveredNode === d.id
        return (
          <g key={`do-${d.id}`}
            onMouseEnter={() => setHoveredNode(d.id)}
            onMouseLeave={() => setHoveredNode(null)}
            style={{ cursor: "pointer" }}
          >
            <rect x={divergeX} y={divergeYs[i] - 12} width={80} height={24} rx={4}
              fill={highlighted ? "var(--test)" : "var(--bg)"}
              stroke="var(--test)"
              strokeWidth={highlighted ? 2 : 1}
              strokeDasharray={highlighted ? "none" : "3 2"}
              opacity={hoveredNode && !highlighted ? 0.3 : 1}
            />
            <text x={divergeX + 40} y={divergeYs[i] + 4} textAnchor="middle"
              fontSize="11" fontFamily="var(--mono)"
              fill={highlighted ? "var(--bg)" : "var(--test)"}>
              {d.token}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

/* ═══════════════════════════════════════════════════════════
   FocalLineScreen — the full screen wrapper
   ═══════════════════════════════════════════════════════════ */

export default function FocalLineScreen({ data, go, runKey }) {
  const focal = data.focal
  const [hoveredNode, setHoveredNode] = useState(null)

  // Find the note for the hovered converge/diverge node
  const hoveredDetail = useMemo(() => {
    if (!hoveredNode) return null
    const cn = focal.converge.find(n => n.id === hoveredNode)
    if (cn) return { label: cn.label, text: cn.note, kind: "converge" }
    const dn = focal.diverge.find(n => n.id === hoveredNode)
    if (dn) return { label: dn.token, text: dn.why, kind: "diverge" }
    return null
  }, [hoveredNode, focal])

  return (
    <div className="screen-inner">
      <div className="kicker"><span className="dot"></span> Step 05 · The mechanism</div>
      <h2 className="display" style={{ marginBottom: 8 }}>The focal line</h2>
      <p className="lede" style={{ maxWidth: "62ch", marginBottom: 28 }}>
        Convergent half = the attribution graph (where meaning concentrates).
        Divergent half = the NLA semantic mirror (why each part attributed; meaning re-expands).
        Hover any node to trace the path.
      </p>

      <div className="two-col" style={{ gridTemplateColumns: "1.4fr 0.6fr", alignItems: "start" }}>
        <div className="panel" style={{ padding: 16 }}>
          <FocalLine focal={focal} hoveredNode={hoveredNode} setHoveredNode={setHoveredNode} />
        </div>
        <div className="stack-lg">
          <div className="panel" style={{
            borderColor: hoveredDetail ? hoveredDetail.kind === "diverge" ? "var(--test)" : "var(--gold)" : "var(--line)",
            transition: "border-color .2s",
            minHeight: 120
          }}>
            {hoveredDetail ? (
              <div>
                <div className="panel-label" style={{ color: hoveredDetail.kind === "diverge" ? "var(--test)" : "var(--gold)" }}>
                  {hoveredDetail.kind === "converge" ? "ATTRIBUTION" : "NLA VERBALIZATION"}
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 14, fontWeight: 700, marginBottom: 6 }}>
                  {hoveredDetail.label}
                </div>
                <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55 }}>
                  {hoveredDetail.text}
                </p>
              </div>
            ) : (
              <div style={{ display: "grid", placeItems: "center", minHeight: 92, textAlign: "center" }}>
                <span className="rail-note" style={{ fontSize: 12 }}>hover a node to<br />read its attribution</span>
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-label test-word">Generated answer</div>
            <p style={{ fontFamily: "var(--display)", fontSize: 18, lineHeight: 1.4, margin: 0 }}>
              "{focal.answer}"
            </p>
          </div>

          <div className="panel">
            <div className="panel-label" style={{ color: "var(--gold)", marginBottom: 8 }}>Reading the diagram</div>
            <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55 }}>
              <strong>Left:</strong> prompt tokens and the knowledge layer enter as inputs.<br />
              <strong>Middle-left:</strong> they activate feature nodes (attribution graph).<br />
              <strong>Centre:</strong> features converge on the focal point — the top logit.<br />
              <strong>Right:</strong> the focal point diverges into the output tokens the model chose.
            </p>
          </div>
        </div>
      </div>

      <div className="nav-row" style={{ marginTop: 40 }}>
        <button className="btn btn-ghost" onClick={() => go(4)}>Back</button>
        <div className="nav-spacer"></div>
        <button className="btn btn-primary" onClick={() => go(0)}>
          Back to the beginning
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13 8H3M7 4L3 8l4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      </div>
    </div>
  )
}
