import React, { useState, useEffect, useRef } from 'react'
import { useTweaks, TweaksPanel, TweakSection, TweakSlider, TweakToggle, TweakColor } from './components/TweaksPanel'
import { fireExperiment, getResults, buildFocal } from './api'
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

export default function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS)
  const [step, setStep] = useState(0)
  const [maxStep, setMaxStep] = useState(0)
  const [mode, setMode] = useState("system_user")
  const [running, setRunning] = useState(false)
  const [runKey, setRunKey] = useState(0)
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
    setRunning(true)  // overlay shows immediately
    const promptEl = document.querySelector('.field textarea.input')
    const klEl = document.querySelector('.field.knowledge textarea.input')
    const prompt = promptEl?.value || data.setup.prompt
    const kl = klEl?.value || data.setup.knowledgeLayer

    // Fire and forget — if connection drops, poll until results appear
    const fetchPromise = fireExperiment({
      prompt, knowledgeLayer: kl,
      nTrials: data.setup.nTrials, injectionMode: mode,
    })

    async function pollUntilDone() {
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 5000))
        try {
          const r = await getResults()
          if (r?.control?.length > 0) return r
        } catch (_) {}
      }
      throw new Error('Experiment did not complete within 5 minutes')
    }

    try {
      const result = await Promise.race([
        fetchPromise,
        // If POST drops, fall back to polling after 10s
        new Promise((resolve, reject) => {
          setTimeout(async () => {
            try { resolve(await pollUntilDone()) }
            catch (e) { reject(e) }
          }, 10000)
        }),
      ])
      setData(prev => ({ ...prev, ...result }))
      setRunKey(k => k + 1)
      go(2)
    } catch (err) {
      console.error('Experiment failed:', err)
      alert('Experiment failed: ' + err.message)
    } finally {
      setRunning(false)
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

        {running && (
          <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", zIndex: 20, background: "#fff" }}>
            <div style={{ textAlign: "center", border: "5px solid #000", background: "#fff", padding: "40px 56px" }}>
              <div style={{ fontFamily: "var(--display)", fontSize: 44, textTransform: "uppercase" }}>Firing volley…</div>
              <div className="rail-note" style={{ marginTop: 10, textTransform: "uppercase", letterSpacing: "1px" }}>{data.setup.nTrials * 2} shots · {data.injectionModes.find(m => m.id === mode).name}</div>
            </div>
          </div>
        )}
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
