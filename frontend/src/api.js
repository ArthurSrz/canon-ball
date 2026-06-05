const API_BASE = '';  // proxied by Vite

export async function fireExperiment({ prompt, knowledgeLayer, nTrials, injectionMode }) {
  const res = await fetch(`${API_BASE}/api/experiment/fire`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, knowledge_layer: knowledgeLayer, n_trials: nTrials, injection_mode: injectionMode }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResults() {
  const res = await fetch(`${API_BASE}/api/experiment/results`);
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

export async function buildFocal({ prompt, knowledgeLayer, maxTokens }) {
  const res = await fetch(`${API_BASE}/api/chain/focal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, knowledge_layer: knowledgeLayer, max_tokens: maxTokens }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
