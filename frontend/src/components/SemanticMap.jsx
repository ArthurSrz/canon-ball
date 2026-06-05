import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Cannon } from './CannonScene'

/* ---------- helpers ---------- */

function ellipseFor(centroids) {
  if (!centroids || centroids.length < 2) return null
  const cx = centroids.reduce((s, p) => s + p.x, 0) / centroids.length
  const cy = centroids.reduce((s, p) => s + p.y, 0) / centroids.length
  const dx = centroids.map((p) => p.x - cx)
  const dy = centroids.map((p) => p.y - cy)
  const rx = Math.max(8, Math.sqrt(dx.reduce((s, v) => s + v * v, 0) / centroids.length) * 2.4)
  const ry = Math.max(8, Math.sqrt(dy.reduce((s, v) => s + v * v, 0) / centroids.length) * 2.4)
  return { cx, cy, rx, ry }
}

function qbez(o, c, t, p) {
  const m = 1 - p
  return {
    x: m * m * o.x + 2 * m * p * c.x + p * p * t.x,
    y: m * m * o.y + 2 * m * p * c.y + p * p * t.y,
  }
}

function easeOutCubic(x) {
  return 1 - Math.pow(1 - x, 3)
}

/* ---------- coordinate mapping ---------- */

const MARGIN = { top: 24, right: 20, bottom: 28, left: 32 }
const W = 420
const H = 300
const innerW = W - MARGIN.left - MARGIN.right
const innerH = H - MARGIN.top - MARGIN.bottom

function toSVG(pt) {
  // data coords: x in [0,1], y in [0,1] → SVG pixel space
  return {
    x: MARGIN.left + pt.x * innerW,
    y: MARGIN.top + (1 - pt.y) * innerH, // y-flip
  }
}

const ORIGIN_SVG = toSVG({ x: 0.05, y: 0.05 })

/* ---------- SemanticMap ---------- */

export default function SemanticMap({
  data = { control: [], test: [] },
  showControl = true,
  showTest = true,
  playful = 0.5,
  runKey = 0,
  motion = true,
  onPick = null,
  picked = null,
}) {
  const [tick, setTick] = useState(0)
  const [hover, setHover] = useState(null)
  const rafRef = useRef(null)
  const startRef = useRef(null)
  const svgRef = useRef(null)

  const cycleDuration = 2.8

  // animation loop
  useEffect(() => {
    if (!motion) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return
    }
    startRef.current = performance.now()
    const loop = (now) => {
      const elapsed = (now - startRef.current) / 1000
      setTick(elapsed)
      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [motion, runKey])

  const cycleT = motion ? Math.min(1, (tick % cycleDuration) / cycleDuration) : 1

  // build shot arrays with SVG positions
  // data entries have {centroid: {x,y}, chunks: [{x,y}], output}
  // normalize to flat {x,y} for SVG mapping
  function normalize(pt) {
    if (pt && pt.centroid) return pt.centroid
    return pt || { x: 0.5, y: 0.5 }
  }

  const controlShots = useMemo(
    () =>
      (data.control || []).map((pt, i) => ({
        ...pt,
        idx: i,
        group: 'control',
        svg: toSVG(normalize(pt)),
      })),
    [data.control],
  )

  const testShots = useMemo(
    () =>
      (data.test || []).map((pt, i) => ({
        ...pt,
        idx: i,
        group: 'test',
        svg: toSVG(normalize(pt)),
      })),
    [data.test],
  )

  // ellipses
  const controlEllipse = useMemo(
    () => ellipseFor(controlShots.map((s) => s.svg)),
    [controlShots],
  )
  const testEllipse = useMemo(
    () => ellipseFor(testShots.map((s) => s.svg)),
    [testShots],
  )

  // steering arrow between centroids
  const steeringArrow = useMemo(() => {
    if (!controlEllipse || !testEllipse) return null
    return {
      x1: controlEllipse.cx,
      y1: controlEllipse.cy,
      x2: testEllipse.cx,
      y2: testEllipse.cy,
    }
  }, [controlEllipse, testEllipse])

  // render a group of shots
  const renderGroup = useCallback(
    (shots, color, show) => {
      if (!show) return null
      const n = shots.length
      return shots.map((shot, i) => {
        const delay = i / (n + 1)
        const ballT = motion ? Math.max(0, Math.min(1, (cycleT - delay * 0.6) / 0.5)) : 1
        const eased = easeOutCubic(ballT)

        // arc from cannon origin to landing point
        const apex = {
          x: (ORIGIN_SVG.x + shot.svg.x) / 2,
          y: Math.min(ORIGIN_SVG.y, shot.svg.y) - 40 - Math.random() * 0, // consistent apex
        }
        const pos = ballT >= 1
          ? shot.svg
          : qbez(ORIGIN_SVG, apex, shot.svg, eased)

        const isLanded = ballT >= 1
        const isPicked =
          picked &&
          picked.group === shot.group &&
          picked.idx === shot.idx
        const r = isPicked ? 5.5 : 3.5

        return (
          <g key={`${shot.group}-${shot.idx}`}>
            {/* trail glow */}
            {!isLanded && ballT > 0 && (
              <circle cx={pos.x} cy={pos.y} r={r + 3} fill={color} opacity={0.1} />
            )}
            {/* shot dot */}
            {ballT > 0 && (
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill={color}
                opacity={isLanded ? 0.75 : 0.9}
                stroke={isPicked ? 'var(--ink)' : 'none'}
                strokeWidth={isPicked ? 2 : 0}
                style={{ cursor: onPick ? 'pointer' : 'default' }}
                onClick={() => onPick && onPick({ group: shot.group, idx: shot.idx })}
                onMouseEnter={() => setHover(shot)}
                onMouseLeave={() => setHover(null)}
              />
            )}
          </g>
        )
      })
    },
    [cycleT, motion, picked, onPick],
  )

  // tooltip
  const tooltip = useMemo(() => {
    if (!hover) return null
    const tx = hover.svg.x + 10
    const ty = hover.svg.y - 10
    const label = hover.label || `${hover.group} #${hover.idx + 1}`
    return (
      <g pointerEvents="none">
        <rect
          x={tx - 2}
          y={ty - 11}
          width={label.length * 5.5 + 12}
          height={16}
          rx="2"
          fill="var(--ink)"
          opacity={0.88}
        />
        <text
          x={tx + 4}
          y={ty}
          fontFamily="var(--mono)"
          fontSize="8"
          fill="var(--void)"
        >
          {label}
        </text>
      </g>
    )
  }, [hover])

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ display: 'block', overflow: 'visible' }}
    >
      <defs>
        <linearGradient id="barrelGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--ink-dim)" />
          <stop offset="100%" stopColor="var(--ink)" />
        </linearGradient>
        <marker id="arrowHead" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
          <polygon points="0 0, 6 2, 0 4" fill="var(--gold)" />
        </marker>
      </defs>

      {/* grid */}
      {[0.0, 0.25, 0.5, 0.75, 1.0].map((v) => {
        const y = MARGIN.top + (1 - v) * innerH
        return (
          <g key={`gy-${v}`}>
            <line x1={MARGIN.left} y1={y} x2={W - MARGIN.right} y2={y}
              stroke="var(--grid)" strokeWidth="0.5" />
            <text x={MARGIN.left - 4} y={y + 3}
              fontFamily="var(--mono)" fontSize="6" fill="var(--ink-faint)"
              textAnchor="end">
              {v.toFixed(2)}
            </text>
          </g>
        )
      })}
      {[0.0, 0.25, 0.5, 0.75, 1.0].map((v) => {
        const x = MARGIN.left + v * innerW
        return (
          <g key={`gx-${v}`}>
            <line x1={x} y1={MARGIN.top} x2={x} y2={H - MARGIN.bottom}
              stroke="var(--grid)" strokeWidth="0.5" />
            <text x={x} y={H - MARGIN.bottom + 12}
              fontFamily="var(--mono)" fontSize="6" fill="var(--ink-faint)"
              textAnchor="middle">
              {v.toFixed(2)}
            </text>
          </g>
        )
      })}

      {/* axis labels */}
      <text x={W / 2} y={H - 4} fontFamily="var(--mono)" fontSize="7"
        fill="var(--ink-dim)" textAnchor="middle">
        UMAP-1
      </text>
      <text x={8} y={H / 2} fontFamily="var(--mono)" fontSize="7"
        fill="var(--ink-dim)" textAnchor="middle"
        transform={`rotate(-90 8 ${H / 2})`}>
        UMAP-2
      </text>

      {/* axes frame */}
      <rect
        x={MARGIN.left} y={MARGIN.top}
        width={innerW} height={innerH}
        fill="none" stroke="var(--line)" strokeWidth="1"
      />

      {/* landing zone ellipses */}
      {showControl && controlEllipse && (
        <ellipse
          cx={controlEllipse.cx} cy={controlEllipse.cy}
          rx={controlEllipse.rx} ry={controlEllipse.ry}
          fill="none" stroke="var(--control)" strokeWidth="1.2"
          strokeDasharray="4 2" opacity={0.45}
        />
      )}
      {showTest && testEllipse && (
        <ellipse
          cx={testEllipse.cx} cy={testEllipse.cy}
          rx={testEllipse.rx} ry={testEllipse.ry}
          fill="none" stroke="var(--test)" strokeWidth="1.2"
          strokeDasharray="4 2" opacity={0.45}
        />
      )}

      {/* steering arrow */}
      {steeringArrow && showControl && showTest && (
        <line
          x1={steeringArrow.x1} y1={steeringArrow.y1}
          x2={steeringArrow.x2} y2={steeringArrow.y2}
          stroke="var(--gold)" strokeWidth="1.5"
          markerEnd="url(#arrowHead)" opacity={0.7}
        />
      )}

      {/* shots */}
      {renderGroup(controlShots, 'var(--control)', showControl)}
      {renderGroup(testShots, 'var(--test)', showTest)}

      {/* cannon in bottom-left */}
      <Cannon x={ORIGIN_SVG.x} y={ORIGIN_SVG.y} scale={0.55} playful={playful}
        charge={motion && cycleT < 0.06 ? Math.sin((cycleT / 0.06) * Math.PI) : 0} />

      {/* tooltip overlay */}
      {tooltip}
    </svg>
  )
}
