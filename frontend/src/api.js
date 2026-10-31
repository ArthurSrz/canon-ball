const API_BASE = '';  // proxied by Vite

export async function fireExperiment({ prompt, knowledgeLayer, nTrials, injectionMode, knowledgeForm, controlKnowledgeForm }) {
  const res = await fetch(`${API_BASE}/api/experiment/fire`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      knowledge_layer: knowledgeLayer,
      n_trials: nTrials,
      injection_mode: injectionMode,
      knowledge_form: knowledgeForm || 'knowledge_graph',
      control_knowledge_form: controlKnowledgeForm || 'prose',
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function previewStructure({ knowledgeLayer, form }) {
  const res = await fetch(`${API_BASE}/api/experiment/structure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ knowledge_layer: knowledgeLayer, form }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResults(experimentId) {
  const params = experimentId ? `?experiment_id=${experimentId}` : '';
  const res = await fetch(`${API_BASE}/api/experiment/results${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function traceChain({ prompt, systemPrompt, maxTokens }) {
  const res = await fetch(`${API_BASE}/api/chain/trace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, system_prompt: systemPrompt, max_tokens: maxTokens }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getChainResults() {
  const res = await fetch(`${API_BASE}/api/chain/results`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getChainStatus() {
  const res = await fetch(`${API_BASE}/api/chain/status`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getChainDiff() {
  const res = await fetch(`${API_BASE}/api/chain/diff`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function buildFocal({ prompt, knowledgeLayer, maxTokens }) {
  const res = await fetch(`${API_BASE}/api/chain/focal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, knowledge_layer: knowledgeLayer, max_tokens: maxTokens }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
