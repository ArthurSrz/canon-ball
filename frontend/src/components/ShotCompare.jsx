import React, { useMemo } from 'react'

/**
 * Two shots, side by side, one from each arm — the control's answer against the test's.
 *
 * The pairing is the reader's: click a black marker and a red one, and whatever you chose
 * lands here. The two arms fire independently, so there is no "same" shot across them;
 * putting shot 3 next to shot 3 would invent a correspondence that does not exist. The
 * reader picks what is worth comparing.
 *
 * The one piece of analysis on top of the raw text is the shared vocabulary: words that
 * occur in BOTH answers are marked. That is what makes the comparison visual rather than
 * a reading exercise — the overlap is where the two arms agree, and everything unmarked
 * is what only one of them said.
 */

// Function words would match in every pair and tell you nothing. Both languages, because
// the knowledge layer can be in either and the model answers in kind.
const STOPWORDS = new Set([
  "the", "and", "that", "this", "with", "from", "they", "them", "their", "there", "these",
  "those", "which", "what", "when", "where", "while", "would", "could", "should", "have",
  "has", "had", "been", "being", "are", "was", "were", "for", "but", "not", "you", "your",
  "its", "it's", "can", "will", "also", "such", "into", "than", "then", "some", "more",
  "most", "like", "just", "about", "other", "over", "only", "very", "here",
  "les", "des", "une", "un", "le", "la", "de", "du", "et", "est", "sont", "dans", "pour",
  "que", "qui", "quoi", "avec", "sur", "par", "pas", "plus", "aux", "ces", "cette", "cet",
  "ils", "elle", "elles", "nous", "vous", "leur", "leurs", "son", "sa", "ses", "comme",
  "mais", "donc", "tout", "tous", "toute", "toutes", "ainsi", "peut", "fait", "faire",
  "ont", "été", "être", "aussi", "entre", "chez", "lors", "voici", "autre", "autres",
])

const MIN_WORD = 4

// French elides before a vowel, so "l'alpinisme" and "alpinisme" are the same word as far
// as a reader is concerned. Without this they would never match.
const ELISION = /^(?:[ldnsjmtc]|qu)['’]/

/** Fold a token to what two answers can be said to share.
 *
 * Lowercase, strip accents, drop a French elision prefix, strip punctuation, then drop a
 * trailing plural "s". That last step is crude — it is not stemming — but it is what makes
 * "himalayiste" and "himalayistes" count as one term, which is most of the value on real
 * answers. Words below MIN_WORD never get here, so it cannot swallow a whole word.
 */
function normalize(word) {
  const folded = word
    .toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(ELISION, "")
    .replace(/[^a-z0-9]/g, "")
  return folded.length > 4 && folded.endsWith("s") ? folded.slice(0, -1) : folded
}

function contentWords(text) {
  const words = new Set()
  for (const raw of (text || "").split(/\s+/)) {
    const word = normalize(raw)
    if (word.length >= MIN_WORD && !STOPWORDS.has(word)) words.add(word)
  }
  return words
}

/** Render text with every shared word marked, keeping the original spacing. */
function Marked({ text, shared, color }) {
  const parts = useMemo(() => (text || "").split(/(\s+)/), [text])
  return (
    <>
      {parts.map((part, i) => {
        if (!part.trim()) return part
        const hit = shared.has(normalize(part))
        return hit ? (
          <mark key={i} style={{
            background: "transparent",
            color,
            fontWeight: 700,
            borderBottom: `2px solid ${color}`,
            padding: 0,
          }}>{part}</mark>
        ) : part
      })}
    </>
  )
}

function Panel({ shot, arm, label, color, empty, shared, maxTokens }) {
  return (
    <div style={{ border: `1.5px solid ${color}`, display: "flex", flexDirection: "column",
                  minHeight: 220 }}>
      <div className="panel-label" style={{
        color, padding: "9px 12px", borderBottom: `1.5px solid ${color}`,
        display: "flex", justifyContent: "space-between", gap: 10,
      }}>
        <span>{label}</span>
        {shot && <span style={{ opacity: 0.6 }}>{arm}</span>}
      </div>

      {shot ? (
        <div style={{ padding: "12px 14px", overflowY: "auto", maxHeight: "38vh" }}>
          <p style={{
            fontFamily: "var(--ui)", fontSize: 15, lineHeight: 1.55, margin: 0,
            whiteSpace: "pre-wrap",
          }}>
            <Marked text={shot.output} shared={shared} color={color} />
          </p>
          {shot.truncated && (
            <div className="rail-note" style={{ marginTop: 10, color: "var(--test)" }}>
              ⚠ cut at the token budget{maxTokens ? ` (${maxTokens} tokens)` : ""} — this
              shot did not finish, so what is missing here is missing from the comparison too.
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: "grid", placeItems: "center", flex: 1, padding: 24,
                      textAlign: "center" }}>
          <span className="rail-note" style={{ fontSize: 12 }}>{empty}</span>
        </div>
      )}
    </div>
  )
}

export default function ShotCompare({ control, test, maxTokens, onClear }) {
  const shared = useMemo(() => {
    if (!control || !test) return new Set()
    const a = contentWords(control.output)
    const b = contentWords(test.output)
    return new Set([...a].filter(w => b.has(w)))
  }, [control, test])

  const both = control && test

  return (
    <div className="panel" style={{ padding: 16, marginTop: 24 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between",
                    gap: 16, flexWrap: "wrap", marginBottom: 12 }}>
        <div className="panel-label">Side by side</div>
        <span className="rail-note" style={{ flex: 1, minWidth: 240 }}>
          {both
            ? <>Words in <b>both</b> answers are underlined — the overlap is where the arms
                agree, and everything plain is what only one of them said.
                {" "}<b>{shared.size}</b> shared {shared.size === 1 ? "term" : "terms"}.</>
            : <>Click a <span className="control-word">black</span> marker and a{" "}
               <span className="test-word">red</span> one. You choose the pair — the arms
               fire independently, so there is no shot that is "the same" across them.</>}
        </span>
        {(control || test) && (
          <button className="btn btn-ghost" onClick={onClear} style={{ padding: "4px 10px" }}>
            Clear
          </button>
        )}
      </div>

      {/* side by side while there is room for it; stacked rather than squeezed below that */}
      <div style={{ display: "grid", gap: 16,
                    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
        <Panel
          shot={control} color="var(--control)"
          label={control ? `CONTROL · shot ${control.idx + 1}` : "CONTROL"}
          arm="no knowledge"
          empty="◉ click a black shot on the map"
          shared={shared} maxTokens={maxTokens}
        />
        <Panel
          shot={test} color="var(--test)"
          label={test ? `TEST · shot ${test.idx + 1}` : "TEST"}
          arm="with knowledge"
          empty="◉ click a red shot on the map"
          shared={shared} maxTokens={maxTokens}
        />
      </div>
    </div>
  )
}
