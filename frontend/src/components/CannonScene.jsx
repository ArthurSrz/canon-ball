import React, { useState, useEffect, useRef, useMemo } from 'react'

/* ---------- helpers ---------- */

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

function seededRandom(seed) {
  let s = seed
  return () => {
    s = (s * 16807 + 0) % 2147483647
    return (s - 1) / 2147483646
  }
}

/* ---------- Cannon SVG group ---------- */

export function Cannon({ x, y, angle = -34, scale = 1, playful = 0.5, charge = 0 }) {
  const recoil = Math.sin(charge * Math.PI) * 4
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      {/* wheel */}
      <circle cx="-4" cy="0" r="13" fill="none" stroke="var(--ink-dim)" strokeWidth="2.4" opacity={0.75} />
      <circle cx="-4" cy="0" r="3.2" fill="var(--ink-dim)" opacity={0.75} />
      {[0, 45, 90, 135].map((a) => (
        <line
          key={a}
          x1="-4" y1="0"
          x2={-4 + 13 * Math.cos((a * Math.PI) / 180)}
          y2={13 * Math.sin((a * Math.PI) / 180)}
          stroke="var(--ink-dim)" strokeWidth="1.4" opacity={0.55}
          transform={`rotate(${a} -4 0)`}
        />
      ))}
      {/* barrel */}
      <g transform={`rotate(${angle}) translate(${-recoil} 0)`}>
        <rect x="-6" y="-7.5" width="40" height="15" rx="7.5"
          fill="url(#barrelGrad)" stroke="var(--line-strong)" strokeWidth="1" />
        <rect x="30" y="-8.5" width="5" height="17" rx="2.5" fill="var(--ink)" opacity={0.85} />
        {/* muzzle flash */}
        {charge > 0.02 && (
          <g opacity={Math.sin(charge * Math.PI)}>
            <circle cx="40" cy="0" r={5 + charge * 9} fill="var(--gold)" opacity={0.8} />
            <circle cx="40" cy="0" r={2 + charge * 5} fill="#fff" />
          </g>
        )}
      </g>
      {/* knowledge ramp */}
      {playful > 0.15 && (
        <g opacity={0.35 + playful * 0.5}>
          <line x1="2" y1="9" x2="30" y2="-12"
            stroke="var(--gold)" strokeWidth={1.5 + playful * 1.5} strokeDasharray="3 3" />
          <text x="16" y="20" fontFamily="var(--mono)" fontSize="6.5"
            fill="var(--gold)" textAnchor="middle" opacity={playful}>
            RAMP
          </text>
        </g>
      )}
    </g>
  )
}

/* ---------- ball generation ---------- */

function generateBalls(seed) {
  const rng = seededRandom(seed)

  // control: 7 cold shots, wide scatter
  const control = Array.from({ length: 7 }, (_, i) => {
    const landX = 260 + (rng() - 0.5) * 120
    const landY = 110 + (rng() - 0.5) * 80
    const apexY = 20 + rng() * 30
    return {
      id: `ctrl-${i}`,
      group: 'control',
      origin: { x: 80, y: 170 },
      control: { x: 120 + rng() * 60, y: apexY },
      target: { x: landX, y: landY },
      delay: i * 0.12,
      r: 3 + rng() * 1.5,
    }
  })

  // test: 6 warm shots, tight cluster
  const test = Array.from({ length: 6 }, (_, i) => {
    const landX = 320 + (rng() - 0.5) * 35
    const landY = 100 + (rng() - 0.5) * 30
    const apexY = 15 + rng() * 25
    return {
      id: `test-${i}`,
      group: 'test',
      origin: { x: 80, y: 170 },
      control: { x: 140 + rng() * 50, y: apexY },
      target: { x: landX, y: landY },
      delay: 0.84 + i * 0.1,
      r: 3 + rng() * 1.5,
    }
  })

  return [...control, ...test]
}

function computeEllipse(balls) {
  if (balls.length < 2) return null
  const cx = balls.reduce((s, b) => s + b.target.x, 0) / balls.length
  const cy = balls.reduce((s, b) => s + b.target.y, 0) / balls.length
  const dx = balls.map((b) => b.target.x - cx)
  const dy = balls.map((b) => b.target.y - cy)
  const rx = Math.max(12, Math.sqrt(dx.reduce((s, v) => s + v * v, 0) / balls.length) * 2.2)
  const ry = Math.max(10, Math.sqrt(dy.reduce((s, v) => s + v * v, 0) / balls.length) * 2.2)
  return { cx, cy, rx, ry }
}

/* ---------- CannonScene ---------- */

export default function CannonScene({ playful = 0.5, motion = true }) {
  const [tick, setTick] = useState(0)
  const rafRef = useRef(null)
  const startRef = useRef(null)
  const balls = useMemo(() => generateBalls(42), [])

  const cycleDuration = 3.2 // seconds per full firing cycle

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
  }, [motion])

  const cycleT = motion ? (tick % cycleDuration) / cycleDuration : 1

  // charge peaks at start of cycle
  const charge = cycleT < 0.08 ? Math.sin((cycleT / 0.08) * Math.PI) : 0

  const controlBalls = balls.filter((b) => b.group === 'control')
  const testBalls = balls.filter((b) => b.group === 'test')
  const controlEllipse = useMemo(() => computeEllipse(controlBalls), [])
  const testEllipse = useMemo(() => computeEllipse(testBalls), [])

  return (
    <svg viewBox="0 0 420 220" width="100%" style={{ display: 'block', overflow: 'visible' }}>
      <defs>
        <linearGradient id="barrelGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--ink-dim)" />
          <stop offset="100%" stopColor="var(--ink)" />
        </linearGradient>
      </defs>

      {/* grid */}
      {[0, 50, 100, 150, 200].map((y) => (
        <line key={`gy-${y}`} x1="0" y1={y} x2="420" y2={y}
          stroke="var(--grid)" strokeWidth="0.5" />
      ))}
      {[0, 50, 100, 150, 200, 250, 300, 350, 400].map((x) => (
        <line key={`gx-${x}`} x1={x} y1="0" x2={x} y2="220"
          stroke="var(--grid)" strokeWidth="0.5" />
      ))}

      {/* ground line */}
      <line x1="0" y1="195" x2="420" y2="195" stroke="var(--ink-dim)" strokeWidth="1" strokeDasharray="4 3" />

      {/* landing zone ellipses */}
      {controlEllipse && (
        <ellipse
          cx={controlEllipse.cx} cy={controlEllipse.cy}
          rx={controlEllipse.rx} ry={controlEllipse.ry}
          fill="none" stroke="var(--control)" strokeWidth="1.2"
          strokeDasharray="4 2" opacity={0.5}
        />
      )}
      {testEllipse && (!motion || cycleT >= 0.5) && (
        <ellipse
          cx={testEllipse.cx} cy={testEllipse.cy}
          rx={testEllipse.rx} ry={testEllipse.ry}
          fill="none" stroke="var(--test)" strokeWidth="1.2"
          strokeDasharray="4 2" opacity={0.5}
        />
      )}

      {/* zone labels removed per design — the legend below carries the signal */}

      {/* balls — control fires first, test waits for control to land */}
      {balls.map((ball) => {
        const ballT = motion
          ? Math.max(0, Math.min(1, (cycleT - ball.delay) / (1 - ball.delay - 0.05)))
          : 1
        if (ball.group === 'test' && motion && cycleT < 0.5) return null
        const eased = easeOutCubic(ballT)
        const pos = ballT >= 1
          ? ball.target
          : qbez(ball.origin, ball.control, ball.target, eased)
        const isLanded = ballT >= 1
        const color = ball.group === 'control' ? 'var(--control)' : 'var(--test)'

        return (
          <g key={ball.id}>
            {/* trail */}
            {!isLanded && ballT > 0 && (
              <circle cx={pos.x} cy={pos.y} r={ball.r + 2}
                fill={color} opacity={0.12} />
            )}
            {/* ball */}
            {ballT > 0 && (
              <circle
                cx={pos.x} cy={pos.y} r={ball.r}
                fill={color}
                opacity={isLanded ? 0.7 : 0.9}
                stroke={isLanded ? color : 'none'}
                strokeWidth={isLanded ? 0.8 : 0}
              />
            )}
          </g>
        )
      })}

      {/* cannon */}
      <Cannon x={80} y={170} playful={playful} charge={charge} />
    </svg>
  )
}
