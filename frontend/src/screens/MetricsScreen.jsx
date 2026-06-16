import React, { useState, useEffect } from 'react'

/* ── count-up hook ── */
function useCountUp(target, duration = 900, active = true) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!active) { setValue(0); return }
    let start = null
    let raf
    function tick(ts) {
      if (!start) start = ts
      const t = Math.min((ts - start) / duration, 1)
      const ease = 1 - Math.pow(1 - t, 3)
      setValue(ease * target)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration, active])
  return value
}

function formatPValue(p) {
  if (p < 1e-4) return 'p < 10⁻⁴'
  if (p < 0.001) return `p = ${p.toExponential(1)}`
  return `p = ${p.toFixed(3)}`
}

export default function MetricsScreen({ data, go, runKey }) {
  const c = data.comparison
  const [active, setActive] = useState(false)

  useEffect(() => {
    setActive(false)
    const id = setTimeout(() => setActive(true), 80)
    return () => clearTimeout(id)
  }, [runKey])

  const dispRatio = useCountUp(c.dispersionRatio, 1000, active)
  const tighten = useCountUp(c.tighteningPct, 1000, active)
  const shift = useCountUp(c.centroidShiftCosine, 1000, active)

  const focused = c.tighteningPct > 0
  const significant = c.mannWhitneyP < 0.05
  const sigPct = Math.min(100, Math.max(4, (1 - c.mannWhitneyP) * 100))

  const ledeText = [
    focused ? 'The scatter tightened' : 'The scatter widened',
    c.centroidShiftCosine > 0.005 ? 'the centre moved' : 'the centre barely moved',
    significant ? 'and the difference is real.' : 'but the difference is not significant.',
  ].join(', ')

  return (
    <div className="screen-inner">
      <div className="kicker"><span className="dot"></span> Step 03 · What the numbers say</div>
      <h2 className="display" style={{ marginBottom: 8 }}>Three measurements</h2>
      <p className="lede" style={{ maxWidth: "58ch", marginBottom: 36 }}>
        {ledeText}
      </p>

      <div className="metrics-row">
        {/* Dispersion ratio */}
        <div className="metric-card">
          <div className="metric-value">{dispRatio.toFixed(3)}</div>
          <div className="metric-label">Dispersion ratio</div>
          <p className="metric-desc">
            Test dispersion / control dispersion. Below 1 = the knowledge layer
            <span className="test-word"> focused</span> the outputs.
          </p>
          <div className="metric-bar">
            <div className="metric-bar-fill focusing" style={{ width: `${Math.min(Math.abs(tighten), 100)}%` }}></div>
          </div>
          <div className="metric-sub">
            {focused
              ? `${tighten.toFixed(1)}% tighter`
              : `${Math.abs(tighten).toFixed(1)}% wider`}
          </div>
        </div>

        {/* Centroid shift */}
        <div className="metric-card">
          <div className="metric-value" style={{ color: "var(--gold)" }}>{shift.toFixed(3)}</div>
          <div className="metric-label">Centroid shift <span style={{ fontSize: 11, opacity: 0.6 }}>(cosine)</span></div>
          <p className="metric-desc">
            How far the centre of meaning moved when knowledge was added.
            This is the <span style={{ color: "var(--gold)" }}>steering</span> effect.
          </p>
          <div className="metric-bar">
            <div className="metric-bar-fill steering" style={{ width: `${Math.min(shift * 100 / 0.05, 100)}%` }}></div>
          </div>
          <div className="metric-sub">{c.centroidShiftEuclidean.toFixed(3)} euclidean</div>
        </div>

        {/* Mann-Whitney U */}
        <div className="metric-card">
          <div className="metric-value">{formatPValue(c.mannWhitneyP)}</div>
          <div className="metric-label">Mann-Whitney U</div>
          <p className="metric-desc">
            {significant
              ? <>The difference between control and test distributions is <strong>statistically significant</strong>. This is not noise.</>
              : <>The difference between control and test distributions is <strong>not statistically significant</strong> (p &gt; 0.05). This could be noise.</>}
          </p>
          <div className="metric-bar">
            <div className={`metric-bar-fill ${significant ? 'significant' : ''}`}
              style={{ width: `${sigPct}%`, background: significant ? undefined : 'var(--ink-faint)' }}></div>
          </div>
          <div className="metric-sub">p = {c.mannWhitneyP.toPrecision(4)}</div>
        </div>
      </div>

      <div className="two-col" style={{ gridTemplateColumns: "1fr 1fr", gap: 32, marginTop: 40 }}>
        <div className="panel">
          <div className="panel-label test-word">Focusing</div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>
            {focused
              ? <>The knowledge layer reduces scatter by <strong>{c.tighteningPct.toFixed(1)}%</strong>. Answers that once sprawled across framings — spiritual, aesthetic, personal — now converge on the disciplined-sport reading the knowledge layer installed.</>
              : <>The knowledge layer <strong>increased</strong> scatter by <strong>{Math.abs(c.tighteningPct).toFixed(1)}%</strong>. The knowledge did not focus outputs — it may have introduced competing framings or the model already had strong priors on this topic.</>}
          </p>
        </div>
        <div className="panel">
          <div className="panel-label" style={{ color: "var(--gold)" }}>Steering</div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>
            The centroid shifts by <strong>{c.centroidShiftCosine.toFixed(4)}</strong> in cosine
            distance. {c.centroidShiftCosine > 0.005
              ? <>The model does not just repeat the knowledge — it adopts a <em>frame</em> that pulls every answer toward a new region of meaning.</>
              : <>The shift is minimal — the knowledge layer did not substantially redirect the model's semantic orientation.</>}
          </p>
        </div>
      </div>

      <div className="nav-row" style={{ marginTop: 40 }}>
        <button className="btn btn-ghost" onClick={() => go(2)}>Back</button>
        <div className="nav-spacer"></div>
        <button className="btn btn-primary" onClick={() => go(4)}>
          Compare injection modes
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      </div>
    </div>
  )
}
