/* Canon Ball — experiment data.
   Numbers are grounded in the real measured results from the repo
   (injection_mode_results.md). Per-trial landing positions are synthesized
   to be statistically faithful to those metrics:
     System -> User: dispersion ratio 0.724 (-27.6%), p < 1e-4, centroid cos-shift 0.020
*/
const MOCK_DATA = (function () {

  // --- deterministic PRNG so the map is stable across reloads ---
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gauss(rng) {
    // Box–Muller
    let u = 0, v = 0;
    while (u === 0) u = rng();
    while (v === 0) v = rng();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  const N = 8;             // trials per group
  const CHUNKS = 5;         // semantic chunks per trial

  // Landing field is a normalized square [0..100] in each axis.
  // Control: wide scatter, cold. Test: tight cluster, warm, shifted.
  const ctrlCenter = { x: 42, y: 56 };
  const testCenter = { x: 58, y: 44 }; // shifted = the "steering" effect
  const ctrlSpread = 17;               // wide landing zone
  const testSpread = 17 * 0.724;       // 0.724 dispersion ratio = focusing

  function makeGroup(seed, center, spread) {
    const rng = mulberry32(seed);
    const trials = [];
    for (let i = 0; i < N; i++) {
      // clamp the centroid offset so neither group throws a wild outlier
      const cx = center.x + Math.max(-1.7, Math.min(1.7, gauss(rng))) * spread;
      const cy = center.y + Math.max(-1.7, Math.min(1.7, gauss(rng))) * spread;
      const chunks = [];
      for (let c = 0; c < CHUNKS; c++) {
        chunks.push({
          x: cx + gauss(rng) * (spread * 0.42),
          y: cy + gauss(rng) * (spread * 0.42),
        });
      }
      trials.push({ index: i, centroid: { x: cx, y: cy }, chunks });
    }
    return trials;
  }

  const control = makeGroup(1337, ctrlCenter, ctrlSpread);
  const test = makeGroup(7331, testCenter, testSpread);

  // ---- Per-trial generated answers (what clicking a shot reveals) ----
  // Control sprawls across framings; test converges on challenge / endurance.
  const controlOutputs = [
    "Some climb for the view — the silence above the clouds.",
    "It's a way to escape the noise of the city and reset.",
    "People chase the thrill of risk and the rush of adrenaline.",
    "For many cultures a mountain is a spiritual pilgrimage.",
    "Curiosity — the simple urge to see what's over the ridge.",
    "For the camaraderie of the rope team and shared hardship.",
    "To feel small against something vast and ancient.",
    "Because the mountain is there, and that is reason enough.",
  ];
  const testOutputs = [
    "People climb to test their limits against the mountain's challenge.",
    "It is the disciplined pursuit of a summit through endurance and skill.",
    "Climbers seek to overcome difficulty — the challenge is the reward.",
    "Mountaineering is a structured feat of endurance and technique.",
    "The drive is to meet a hard challenge and prove one's resolve.",
    "Ascending demands skill, endurance, and the will to push limits.",
    "People climb to face the challenge and master the ascent.",
    "A deliberate test of body and will against the peak.",
  ];
  control.forEach((t, i) => { t.output = controlOutputs[i % controlOutputs.length]; });
  test.forEach((t, i) => { t.output = testOutputs[i % testOutputs.length]; });

  // ---- The experiment setup (mirrors the real alpinism/Wikidata run) ----
  const setup = {
    prompt: "Write a short reflection on why people climb mountains.",
    knowledgeLayer:
      "Mountaineering (alpinism) is the set of sporting and leisure activities " +
      "that involve ascending mountains — including rock climbing, ice climbing, " +
      "ski touring and hiking across glaciated terrain. It emerged in the Alps " +
      "in the 18th century and is governed today by national alpine federations.",
    knowledgeSource: "Wikidata — Q43482 “mountaineering”",
    nTrials: N,
    model: "qwen2.5",
    embedder: "bge-m3",
  };

  // ---- Headline comparison (System -> User mode) ----
  const comparison = {
    controlMeanDispersion: 0.1183,
    testMeanDispersion: 0.0857,
    dispersionRatio: 0.724,
    tighteningPct: 27.6,
    centroidShiftCosine: 0.020,
    centroidShiftEuclidean: 0.214,
    mannWhitneyP: 0.0001, // reported as < 1e-4
  };

  // ---- Injection modes (real table) ----
  const injectionModes = [
    {
      id: "system_user", name: "System → User", ratio: 0.724, tighten: 27.6,
      p: "< 1e-4", pVal: 0.00009, shift: 0.020, rank: 1,
      how: "Knowledge in a system message, prompt in a separate user message.",
      why: "The system slot carries an implicit trust signal that concentrates output around the knowledge.",
    },
    {
      id: "template", name: "Template injection", ratio: 0.786, tighten: 21.4,
      p: "0.030", pVal: 0.030, shift: 0.019, rank: 2,
      how: "prompt + “---\\nContext:\\n” + knowledge, all in one user message.",
      why: "The “---” separator is enough for the model to treat knowledge as reference material — without a system slot's privilege.",
    },
    {
      id: "cot_priming", name: "CoT priming", ratio: 0.816, tighten: 18.4,
      p: "0.012", pVal: 0.012, shift: 0.024, rank: 3,
      how: "Knowledge injected as a fake earlier assistant turn (“what do you know?” → knowledge → prompt).",
      why: "Framing knowledge as something the model “already said” moves the centre of the answer the most — biggest steer, looser focus.",
    },
    {
      id: "interleave", name: "Interleaved", ratio: 0.894, tighten: 10.6,
      p: "0.100", pVal: 0.100, shift: 0.015, rank: 4,
      how: "Knowledge paragraphs slotted between the prompt's sentences, one user message.",
      why: "Fragmenting the knowledge across the prompt destroys its coherence — the weakest effect, not significant.",
    },
  ];

  // ---- Neuronpedia: per-token activation descriptions (NLA verbalizer) ----
  // Response the model produced (test condition), tokenized.
  const responseTokens = [
    { t: "People", desc: "Activates on words introducing human collective subjects." },
    { t: " climb", desc: "Strong response to verbs of vertical physical ascent." },
    { t: " mountains", desc: "Fires on large natural elevated landforms; peaks, ranges." },
    { t: " to", desc: "Low-salience function token linking motive clauses." },
    { t: " feel", desc: "Responds to verbs of subjective interior experience." },
    { t: " the", desc: "Determiner; minimal independent activation." },
    { t: " thin", desc: "Activates on descriptors of rarefied, sparse physical media." },
    { t: " air", desc: "Fires on atmosphere / breathable-medium concepts." },
    { t: " of", desc: "Function token; near-zero activation." },
    { t: " altitude", desc: "High response to elevation and height-above-sea-level concepts." },
    { t: ",", desc: "Punctuation boundary; clause segmentation." },
    { t: " to", desc: "Function token linking purpose." },
    { t: " test", desc: "Activates on words of trial, challenge, and proving." },
    { t: " their", desc: "Possessive pronoun; references prior subject." },
    { t: " limits", desc: "Fires on concepts of boundary, capacity, and extremity." },
    { t: ".", desc: "Sentence terminator." },
  ];

  // ---- Attribution graph (Circuit Tracer–style): prompt -> features -> logit ----
  const graph = {
    promptTokens: ["Why", " do", " people", " climb", " mountains", "?"],
    features: [
      { id: "f-asc", label: "ascent / vertical motion", layer: 14, influence: 0.91 },
      { id: "f-nat", label: "natural landforms", layer: 11, influence: 0.74 },
      { id: "f-chal", label: "challenge & endurance", layer: 18, influence: 0.83 },
      { id: "f-exp", label: "subjective experience", layer: 21, influence: 0.67 },
      { id: "f-alp", label: "alpinism domain (knowledge layer)", layer: 16, influence: 0.88, fromKnowledge: true },
    ],
    logits: [
      { id: "l-challenge", label: "challenge", p: 0.34 },
      { id: "l-because", label: "because", p: 0.21 },
      { id: "l-feeling", label: "feeling", p: 0.16 },
    ],
    // edges: source -> target with signed weight
    edges: [
      { s: "p-climb", t: "f-asc", w: 0.92 },
      { s: "p-mountains", t: "f-nat", w: 0.81 },
      { s: "p-climb", t: "f-chal", w: 0.55 },
      { s: "p-people", t: "f-exp", w: 0.48 },
      { s: "k", t: "f-alp", w: 0.96 },
      { s: "f-alp", t: "f-chal", w: 0.61 },
      { s: "f-alp", t: "f-asc", w: 0.34 },
      { s: "f-asc", t: "l-challenge", w: 0.72 },
      { s: "f-chal", t: "l-challenge", w: 0.66 },
      { s: "f-exp", t: "l-feeling", w: 0.58 },
      { s: "f-nat", t: "l-because", w: 0.29 },
      { s: "f-alp", t: "l-challenge", w: 0.44 },
    ],
  };

  // ---- The Focal Line — the mechanism behind the focusing ----
  // Convergent half = attribution graph (knowledge objects where meaning concentrates).
  // Divergent half  = NLA semantic mirror (why each part attributed; meaning re-expands).
  const focal = {
    inputs: [
      { id: "why", label: "why", kind: "prompt" },
      { id: "people", label: "people", kind: "prompt" },
      { id: "climb", label: "climb", kind: "prompt" },
      { id: "mountains", label: "mountains", kind: "prompt" },
      { id: "know", label: "knowledge layer", kind: "know" },
    ],
    converge: [
      { id: "asc", label: "ascent · vertical motion", from: ["climb"], w: 0.92,
        note: "The verb “climb” ignites a feature for upward physical movement." },
      { id: "nat", label: "natural landforms", from: ["mountains"], w: 0.78,
        note: "“mountains” lights up a feature for large elevated terrain." },
      { id: "chal", label: "challenge · endurance", from: ["climb", "know"], w: 0.86, hot: true,
        note: "Prompt and knowledge layer BOTH feed this node — the convergence point of the focusing." },
      { id: "alp", label: "alpinism frame", from: ["know"], w: 0.96, gold: true,
        note: "The knowledge layer installs the disciplined-sport sense of mountaineering." },
      { id: "exp", label: "subjective experience", from: ["people"], w: 0.52,
        note: "“people” activates a weaker feature for interior, felt experience." },
    ],
    focus: { label: "challenge", p: 0.34 },
    answer: "People climb to test their limits against the mountain's challenge.",
    diverge: [
      { id: "d1", token: "challenge", why: "Selected because the alpinism frame foregrounds difficulty and feats of endurance." },
      { id: "d2", token: "limits", why: "A boundary / capacity feature, pushed by “test their limits.”" },
      { id: "d3", token: "endurance", why: "The knowledge layer supplies the disciplined-sport reading of the climb." },
      { id: "d4", token: "ascent", why: "Verbalizes the vertical-motion feature that “climb” first ignited." },
    ],
  };

  return {
    setup, control, test, comparison, injectionModes,
    responseTokens, graph, focal,
    N, field: { ctrlCenter, testCenter, ctrlSpread, testSpread },
  };
})();

export default MOCK_DATA;
