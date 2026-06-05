import React, { useState, useCallback, useEffect } from 'react'

/* ── hook ── */
export function useTweaks(defaults) {
  const [values, setValues] = useState(() => ({ ...defaults }))
  const setTweak = useCallback((key, value) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }, [])
  return [values, setTweak]
}

/* ── inline styles ── */
const STYLE = `
.tweaks-toggle {
  position: fixed; bottom: 16px; right: 16px; z-index: 9999;
  width: 36px; height: 36px; border-radius: 50%;
  border: 1.5px solid var(--line-strong, #333);
  background: var(--bg, #fff); cursor: pointer;
  display: grid; place-items: center;
  font-size: 16px; line-height: 1;
  box-shadow: 0 2px 8px rgba(0,0,0,.12);
}
.tweaks-panel {
  position: fixed; bottom: 60px; right: 16px; z-index: 9998;
  width: 260px; max-height: 70vh; overflow-y: auto;
  background: var(--bg, #fff);
  border: 1.5px solid var(--line-strong, #333);
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,.10);
  font-family: var(--sans, system-ui, sans-serif);
  font-size: 12px;
}
.tweaks-panel-title {
  font-weight: 700; font-size: 11px; text-transform: uppercase;
  letter-spacing: 1.2px; margin-bottom: 10px; opacity: .6;
}
.tweak-section {
  font-weight: 700; font-size: 10px; text-transform: uppercase;
  letter-spacing: 1px; margin: 12px 0 6px; opacity: .5;
}
.tweak-row {
  display: flex; align-items: center; justify-content: space-between;
  margin: 6px 0;
}
.tweak-row label { flex: 1; opacity: .8; }
.tweak-row input[type="range"] { width: 100px; }
.tweak-row .toggle {
  width: 36px; height: 20px; border-radius: 10px;
  background: #ccc; position: relative; cursor: pointer;
  border: none; padding: 0; transition: background .2s;
}
.tweak-row .toggle.on { background: var(--test, #ff0000); }
.tweak-row .toggle::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 16px; height: 16px; border-radius: 50%;
  background: #fff; transition: transform .2s;
}
.tweak-row .toggle.on::after { transform: translateX(16px); }
.tweak-color-opts { display: flex; gap: 4px; }
.tweak-color-opt {
  display: flex; gap: 2px; padding: 3px 5px; border-radius: 4px;
  border: 1.5px solid transparent; cursor: pointer; background: none;
}
.tweak-color-opt.active { border-color: var(--line-strong, #333); }
.tweak-color-swatch {
  width: 14px; height: 14px; border-radius: 3px;
  border: 1px solid rgba(0,0,0,.15);
}
`

let styleInjected = false

function injectStyle() {
  if (styleInjected) return
  styleInjected = true
  const el = document.createElement('style')
  el.textContent = STYLE
  document.head.appendChild(el)
}

/* ── components ── */

export function TweaksPanel({ title, children }) {
  const [open, setOpen] = useState(false)

  useEffect(() => { injectStyle() }, [])

  return (
    <>
      <button className="tweaks-toggle" onClick={() => setOpen(o => !o)} aria-label="Toggle tweaks">
        {open ? '✕' : '⚙'}
      </button>
      {open && (
        <div className="tweaks-panel">
          {title && <div className="tweaks-panel-title">{title}</div>}
          {children}
        </div>
      )}
    </>
  )
}

export function TweakSection({ label }) {
  return <div className="tweak-section">{label}</div>
}

export function TweakSlider({ label, value, min = 0, max = 100, unit = '', onChange }) {
  return (
    <div className="tweak-row">
      <label>{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
      />
    </div>
  )
}

export function TweakToggle({ label, value, onChange }) {
  return (
    <div className="tweak-row">
      <label>{label}</label>
      <button
        className={'toggle' + (value ? ' on' : '')}
        onClick={() => onChange(!value)}
        aria-pressed={value}
      />
    </div>
  )
}

export function TweakColor({ label, value, options, onChange }) {
  return (
    <div>
      <div className="tweak-row"><label>{label}</label></div>
      <div className="tweak-color-opts">
        {options.map((opt, i) => {
          const active = JSON.stringify(opt) === JSON.stringify(value)
          return (
            <button
              key={i}
              className={'tweak-color-opt' + (active ? ' active' : '')}
              onClick={() => onChange(opt)}
            >
              {opt.map((c, j) => (
                <div key={j} className="tweak-color-swatch" style={{ background: c }} />
              ))}
            </button>
          )
        })}
      </div>
    </div>
  )
}
