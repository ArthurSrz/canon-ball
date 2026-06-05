import React, { useState, useEffect } from 'react'
import { useTweaks, TweaksPanel, TweakSection, TweakSlider, TweakToggle, TweakColor } from './components/TweaksPanel'
import { buildFocal } from './api'
import { useExperiment } from './hooks/useExperiment'
import MOCK_DATA from './mockData'
import ConceptScreen from './screens/ConceptScreen'
import SetupScreen from './screens/SetupScreen'
import MapScreen from './screens/MapScreen'
import MetricsScreen from './screens/MetricsScreen'
import ModesScreen from './screens/ModesScreen'
import FocalLineScreen from './screens/FocalLineScreen'

const STEPS = [
  { n: "00", label: "Concept" },
  { n: "01", label: "Load the canon" },
  { n: "02", label: "Landing map" },
  { n: "03", label: "Measurements" },
  { n: "04", label: "Injection modes" },
  { n: "05", label: "The focal line" },
]

const TWEAK_DEFAULTS = {
  metaphor: 50,
  motion: true,
  accent: ["#000000", "#FF0000"],
}

function hexToRgba(hex, a) {
  const n = parseInt(hex.replace("#", ""), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

function FiringOverlay({ nTrials, modeName }) {
  const [frame, setFrame] = useState(0)
  const [msg, setMsg] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setFrame(f => f + 1), 80)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const id = setInterval(() => setMsg(m => (m + 1) % MSGS.length), 3000)
    return () => clearInterval(id)
  }, [])

  const MSGS = [
    "Loading the powder…",
    "Consulting the Library of Babel…",
    "Tokens incoming…",
    "The chain is forming…",
    "Measuring semantic dispersion…",
    "Almost there — stay calm…",
    "Gemma is thinking…",
    "Activating features…",
  ]

  const angle = (frame * 6) % 360  // wheel spin

  return (
    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", zIndex: 20, background: "#fff" }}>
      <div style={{ textAlign: "center", border: "5px solid #000", background: "#fff", padding: "48px 64px", maxWidth: 480 }}>

        {/* Spinning cannon wheel */}
        <svg width="80" height="80" viewBox="0 0 80 80" style={{ display: "block", margin: "0 auto 24px" }}>
          {/* wheel rim */}
          <circle cx="40" cy="40" r="32" fill="none" stroke="#000" strokeWidth="4" />
          {/* spokes — rotate */}
          <g transform={`rotate(${angle} 40 40)`}>
            {[0,45,90,135].map(a => (
              <line key={a} x1="40" y1="40"
                x2={40 + 32 * Math.cos(a * Math.PI / 180)}
                y2={40 + 32 * Math.sin(a * Math.PI / 180)}
                stroke="#000" strokeWidth="2.5" />
            ))}
          </g>
          {/* hub */}
          <circle cx="40" cy="40" r="6" fill="#000" />
          {/* cannon barrel */}
          <rect x="48" y="34" width="22" height="12" rx="6" fill="#000" />
          {/* muzzle flash — blink */}
          {frame % 8 < 2 && (
            <circle cx="72" cy="40" r={4 + (frame % 3)} fill="var(--gold)" opacity="0.9" />
          )}
          {/* ball in flight */}
          <circle cx={48 + ((frame * 3) % 30)} cy={40 - ((frame * 3) % 30) * 0.4}
            r="3" fill="var(--test)" opacity={((frame * 3) % 30) < 20 ? 1 : 0} />
        </svg>

        <div style={{ fontFamily: "var(--display)", fontSize: 36, textTransform: "uppercase", lineHeight: 1.1 }}>
          Firing volley…
        </div>
        <div className="rail-note" style={{ marginTop: 8, textTransform: "uppercase", letterSpacing: "1px" }}>
          {nTrials * 2} shots · {modeName}
        </div>
        <div style={{ marginTop: 20, fontFamily: "var(--mono)", fontSize: 12, color: "#555", minHeight: 18, transition: "opacity 0.3s" }}>
          {MSGS[msg]}
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS)
  const [step, setStep] = useState(0)
  const [maxStep, setMaxStep] = useState(0)
  const [mode, setMode] = useState("template")
  const [runKey, setRunKey] = useState(0)
  const { fire: hookFire, status: experimentStatus } = useExperiment()
  const running = experimentStatus === 'firing' || experimentStatus === 'polling'
  const [data, setData] = useState(MOCK_DATA)

  const playful = (t.metaphor ?? 50) / 100
  const [ctrlCol, testCol] = t.accent || ["#000000", "#FF0000"]

  useEffect(() => {
    const r = document.documentElement.style
    r.setProperty("--playful", String(playful))
    r.setProperty("--control", ctrlCol)
    r.setProperty("--control-glow", hexToRgba(ctrlCol, 0.55))
    r.setProperty("--test", testCol)
    r.setProperty("--test-glow", hexToRgba(testCol, 0.55))
  }, [playful, ctrlCol, testCol])

  function go(s) {
    setStep(s)
    setMaxStep(m => Math.max(m, s))
    document.querySelectorAll(".screen").forEach(el => { el.scrollTop = 0 })
  }

  async function fire() {
    const promptEl = document.querySelector('.field textarea.input')
    const klEl = document.querySelector('.field.knowledge textarea.input')
    const prompt = promptEl?.value || data.setup.prompt
    const kl = klEl?.value || data.setup.knowledgeLayer

    try {
      const result = await hookFire({
        prompt,
        knowledgeLayer: kl,
        nTrials: data.setup.nTrials,
        injectionMode: mode,
      })
      setData(prev => ({ ...prev, ...result }))
      setRunKey(k => k + 1)
      go(2)
    } catch (err) {
      console.error('Experiment failed:', err)
      alert('Experiment failed: ' + err.message)
    }
  }

  function replay() { setRunKey(k => k + 1) }

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 40 40" fill="none">
            <circle cx="20" cy="20" r="18" stroke="var(--line-strong)" strokeWidth="1.5" />
            <circle cx="26" cy="14" r="5" fill="var(--test)" style={{ filter: "drop-shadow(0 0 6px var(--test-glow))" }} />
            <circle cx="12" cy="25" r="2.4" fill="var(--control)" />
            <circle cx="16" cy="29" r="2.4" fill="var(--control)" />
            <circle cx="11" cy="18" r="2.4" fill="var(--control)" opacity="0.7" />
            <path d="M6 30 Q16 8 30 12" stroke="var(--gold)" strokeWidth="1" strokeDasharray="2 2" fill="none" opacity="0.6" />
          </svg>
          <div>
            <div className="brand-name">Canon&nbsp;Ball</div>
            <div className="brand-sub">Ballistics of Meaning</div>
          </div>
        </div>
        <div className="rail-divider"></div>
        <div className="steps">
          {STEPS.map((s, i) => (
            <button
              key={s.n}
              className={"step-btn" + (step === i ? " active" : "") + (i < maxStep && step !== i ? " done" : "")}
              disabled={i > maxStep}
              onClick={() => i <= maxStep && go(i)}
              style={{ opacity: i > maxStep ? 0.4 : 1 }}
            >
              <span className="step-num">{s.n}</span>
              {s.label}
            </button>
          ))}
        </div>
      </aside>

      <main className="stage">
        <div className={"screen" + (step === 0 ? " show" : "")}><ConceptScreen playful={playful} go={go} motion={t.motion} /></div>
        <div className={"screen" + (step === 1 ? " show" : "")}><SetupScreen data={data} playful={playful} go={go} mode={mode} setMode={setMode} running={running} fire={fire} /></div>
        <div className={"screen" + (step === 2 ? " show" : "")}><MapScreen data={data} playful={playful} go={go} runKey={runKey} replay={replay} motion={t.motion} /></div>
        <div className={"screen" + (step === 3 ? " show" : "")}>{step === 3 && <MetricsScreen data={data} go={go} runKey={runKey} />}</div>
        <div className={"screen" + (step === 4 ? " show" : "")}><ModesScreen data={data} go={go} /></div>
        <div className={"screen" + (step === 5 ? " show" : "")}>{step === 5 && <FocalLineScreen data={data} go={go} runKey={runKey} />}</div>

        {running && <FiringOverlay nTrials={data.setup.nTrials} modeName={data.injectionModes.find(m => m.id === mode)?.name} />}
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Metaphor" />
        <TweakSlider label="Scientific ↔ Playful" value={t.metaphor} min={0} max={100} unit="" onChange={v => setTweak("metaphor", v)} />
        <TweakToggle label="Motion" value={t.motion} onChange={v => setTweak("motion", v)} />
        <TweakSection label="Signal colors" />
        <TweakColor label="Control · Test" value={t.accent} options={[["#000000", "#FF0000"], ["#000000", "#FFA500"], ["#000000", "#008000"], ["#FF0000", "#000000"]]} onChange={v => setTweak("accent", v)} />
      </TweaksPanel>
    </div>
  )
}
