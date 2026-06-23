import React from 'react'
import CannonScene from '../components/CannonScene'

export default function ConceptScreen({ playful, go, motion }) {
  return (
    <div className="screen-inner">
      <div className="two-col" style={{ alignItems: "center" }}>
        <div>
          <h1 className="display fu" style={{ animationDelay: ".05s" }}>
            What do <em>knowledge layers</em> do<br />to language models?
          </h1>
          <p className="lede fu" style={{ animationDelay: ".2s" }}>
            Picture a cannon. Load it with a prompt, light the charge, and the model's
            answer lands somewhere in a wide field of meaning. Fire again — another shot,
            another landing. Ask the same thing a hundred times and the shots
            <strong> scatter</strong>: the model means a hundred slightly different things.
          </p>
          <p className="lede fu" style={{ animationDelay: ".32s" }}>
            Now pack a <span style={{ color: "var(--gold)" }}>knowledge layer</span> behind
            the powder and fire the same volley. The shots fall tighter, and somewhere new —
            the scatter <span className="test-word">tightens</span> and
            <span style={{ color: "var(--gold)" }}> shifts</span>, as if the barrel were
            rifled, as if every answer passed through a <em>focal line</em>.
            <strong> Canon&nbsp;Ball</strong> measures that change — so what knowledge does to
            a model stops being a hand-wave and becomes a number.
          </p>
          <div className="nav-row fu" style={{ animationDelay: ".5s" }}>
            <button className="btn btn-primary" onClick={() => go(1)}>
              Set up an experiment
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
            <button className="btn btn-ghost" onClick={() => go(2)}>Skip to results</button>
          </div>
        </div>
        <div className="fu" style={{ animationDelay: ".3s" }}>
          <div className="panel" style={{ padding: 14 }}>
            <CannonScene playful={playful} motion={motion} />
            <div className="legend" style={{ justifyContent: "center", marginTop: 6 }}>
              <span className="lg"><span className="sw c"></span> without KL</span>
              <span className="lg"><span className="sw t"></span> with KL</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
