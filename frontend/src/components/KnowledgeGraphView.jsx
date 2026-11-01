import React, { useMemo, useState } from 'react'

/**
 * Draws the graph the test arm is loaded with — a radial tree rooted on the head subject.
 *
 * The point of the drawing is verification, not decoration: hovering any node or edge
 * lights up every edge the same claim produced and prints that claim verbatim underneath,
 * so a researcher can check that the extractor read the prose the way they think it did.
 */

const VIEW_W = 1400
const VIEW_H = 780
const CX = VIEW_W / 2
const CY = VIEW_H / 2
const RX = 245          // ellipse radii per depth — wider than tall, like the panel
const RY = 155
const MAX_LABEL = 28

const KIND = {
  entity: { fill: "var(--control)", r: 7, text: "entity" },
  value: { fill: "var(--gold)", r: 6, text: "value" },
  concept: { fill: "#ffffff", r: 5.5, text: "concept" },
}

function truncate(label) {
  return label.length > MAX_LABEL ? label.slice(0, MAX_LABEL - 1) + "…" : label
}

/** Parent every node by the first edge that reaches it, then lay the tree out radially. */
function layout(graph) {
  const nodes = graph?.nodes || []
  const edges = graph?.edges || []
  if (!nodes.length) return { placed: [], links: [], root: null }

  const firstIn = new Map()
  for (const e of edges) if (!firstIn.has(e.target)) firstIn.set(e.target, e)

  const hasOut = new Set(edges.map(e => e.source))
  const root = nodes.find(n => !firstIn.has(n.id) && hasOut.has(n.id)) || nodes[0]

  const children = new Map()
  for (const n of nodes) {
    if (n.id === root.id) continue
    const parent = firstIn.get(n.id)?.source ?? root.id   // orphans hang off the root
    if (!children.has(parent)) children.set(parent, [])
    children.get(parent).push(n.id)
  }

  // Angular span is proportional to leaf count, so a hub with ten targets gets ten slots.
  const leafCount = new Map()
  const countLeaves = (id, seen = new Set()) => {
    if (seen.has(id)) return 0
    seen.add(id)
    const kids = children.get(id) || []
    const total = kids.length ? kids.reduce((a, k) => a + countLeaves(k, seen), 0) : 1
    leafCount.set(id, total)
    return total
  }
  countLeaves(root.id)

  const pos = new Map()
  const place = (id, from, to, depth, seen) => {
    if (seen.has(id)) return
    seen.add(id)
    const angle = (from + to) / 2
    pos.set(id, {
      x: depth === 0 ? CX : CX + Math.cos(angle) * RX * depth,
      y: depth === 0 ? CY : CY + Math.sin(angle) * RY * depth,
      angle, depth,
    })
    const kids = children.get(id) || []
    const total = kids.reduce((a, k) => a + (leafCount.get(k) || 1), 0) || 1
    let cursor = from
    for (const kid of kids) {
      const span = (to - from) * ((leafCount.get(kid) || 1) / total)
      place(kid, cursor, cursor + span, depth + 1, seen)
      cursor += span
    }
  }
  place(root.id, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2, 0, new Set())

  const placed = nodes.filter(n => pos.has(n.id)).map(n => ({ ...n, ...pos.get(n.id) }))
  const links = edges
    .filter(e => pos.has(e.source) && pos.has(e.target))
    .map(e => ({ ...e, a: pos.get(e.source), b: pos.get(e.target), tree: firstIn.get(e.target) === e }))

  return { placed, links, root }
}

export default function KnowledgeGraphView({ graph, claims = [] }) {
  const [focus, setFocus] = useState(null)   // claim index under the pointer
  const { placed, links, root } = useMemo(() => layout(graph), [graph])

  if (!placed.length) {
    return (
      <div style={{ border: "1.5px solid var(--line-strong, #333)", padding: "28px 12px",
                    textAlign: "center", fontFamily: "var(--mono)", fontSize: 12, opacity: 0.5 }}>
        (no graph yet — write some prose above)
      </div>
    )
  }

  const lit = i => focus === null || focus === i
  const claim = claims.find(c => c.index === focus)
  const litEdges = focus === null ? [] : links.filter(e => e.claimIndex === focus)

  return (
    <div style={{ border: "1.5px solid var(--line-strong, #333)" }}>
      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} style={{ width: "100%", height: "auto", display: "block" }}
        onMouseLeave={() => setFocus(null)}>
        <g>
          {links.map((e, i) => (
            <g key={`e${i}`} onMouseEnter={() => setFocus(e.claimIndex)} style={{ cursor: "crosshair" }}>
              {/* a fat invisible line so the edge is hoverable without pixel-hunting */}
              <line x1={e.a.x} y1={e.a.y} x2={e.b.x} y2={e.b.y} stroke="transparent" strokeWidth="12" />
              <line
                x1={e.a.x} y1={e.a.y} x2={e.b.x} y2={e.b.y}
                stroke={lit(e.claimIndex) ? "var(--control)" : "var(--control)"}
                strokeWidth={focus === e.claimIndex ? 2.2 : 1}
                strokeDasharray={e.tree ? undefined : "3 3"}
                opacity={lit(e.claimIndex) ? (focus === e.claimIndex ? 1 : 0.55) : 0.1}
              />
              <text
                x={e.a.x + (e.b.x - e.a.x) * 0.68} y={e.a.y + (e.b.y - e.a.y) * 0.68 - 4}
                textAnchor="middle" fontFamily="var(--mono)" fontSize="9"
                fill={focus === e.claimIndex ? "var(--test)" : "var(--control)"}
                opacity={focus === e.claimIndex ? 1 : (focus === null ? 0.5 : 0.08)}
              >{e.relation}</text>
            </g>
          ))}
        </g>

        <g>
          {placed.map(n => {
            const style = KIND[n.kind] || KIND.concept
            const isRoot = n.id === root.id
            const touching = focus === null
              || litEdges.some(e => e.source === n.id || e.target === n.id)
            const right = Math.cos(n.angle) >= 0 || isRoot
            const r = isRoot ? 11 : style.r
            return (
              <g key={n.id} opacity={touching ? 1 : 0.15}
                onMouseEnter={() => {
                  const inbound = links.find(e => e.target === n.id)
                  setFocus(inbound ? inbound.claimIndex : null)
                }}
                style={{ cursor: "crosshair" }}>
                <circle cx={n.x} cy={n.y} r={r} fill={isRoot ? "var(--test)" : style.fill}
                  stroke="var(--control)" strokeWidth="1.5" />
                <text
                  x={isRoot ? n.x : n.x + (right ? r + 6 : -(r + 6))}
                  y={isRoot ? n.y - 18 : n.y + 3.5}
                  textAnchor={isRoot ? "middle" : (right ? "start" : "end")}
                  fontFamily="var(--mono)"
                  fontSize={isRoot ? 14 : 11}
                  fontWeight={isRoot ? 700 : 400}
                  fill="var(--ink, #000)"
                >{truncate(n.label)}<title>{n.label}</title></text>
              </g>
            )
          })}
        </g>
      </svg>

      <div style={{ borderTop: "1.5px solid var(--line-strong, #333)", padding: "8px 12px",
                    display: "flex", gap: 18, alignItems: "baseline", flexWrap: "wrap" }}>
        <span className="rail-note" style={{ whiteSpace: "nowrap" }}>
          {Object.entries(KIND).map(([kind, s]) => (
            <span key={kind} style={{ marginRight: 12 }}>
              <span style={{
                display: "inline-block", width: 9, height: 9, borderRadius: "50%",
                background: s.fill, border: "1.5px solid var(--control)",
                marginRight: 4, verticalAlign: "middle",
              }} />{kind}
            </span>
          ))}
          <span style={{ opacity: 0.6 }}>┄ a node two claims share</span>
        </span>
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, flex: 1, minWidth: 260 }}>
          {claim
            ? <><span style={{ color: "var(--test)" }}>[{claim.relation}]</span> {claim.text}</>
            : <span style={{ opacity: 0.5 }}>Hover a node or an edge to read the claim it was extracted from.</span>}
        </span>
      </div>
    </div>
  )
}
