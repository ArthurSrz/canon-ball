# Troubleshooting & API Notes

## Neuronpedia NLA (Natural Language Autoencoder) public API — confirmed contract

Confirmed by reading the source of `hijohnnylin/neuronpedia` (the swagger blocks in
`apps/webapp/app/api/nla/{sources,completion,explain}/route.ts`) on 2026-05-21, because the
public API doc page (`/api-doc`) is a JS-rendered Scalar app that WebFetch can't read.

**Base URL:** `https://www.neuronpedia.org`
**Auth:** *optional* — routes use `withOptionalUser` and declare `security: [apiKey, {}]`.
Calls work key-less but are rate-limited per IP. Send the key as header `x-api-key` to raise limits.
**Rate limits (key-less):** completion 240/hr, explain 120/hr.

### The 3-call loop

1. **`GET /api/nla/sources`** → `{ sources: [{ modelId, id, displayName, description, url,
   author, av, ar, layerNum, norm, model:{ id, displayName, openRouterAvailable } }] }`
   - `id` is the value you pass as `nlaSourceId`.
   - `model.openRouterAvailable` must be `true` to use the completion *generation* path.

2. **`POST /api/nla/completion`**
   - Body: `{ modelId, messages:[{role,content}], completion_tokens (≤512), temperature (def 0.7) }`
   - Returns (non-streaming, the default for API callers): `{ completion, full_text, tokens:[{token, token_id, position}] }`
   - `full_text` is the chat-templated `prompt + assistant turn`. Pass it as `text` to `/explain`.
   - `tokens[*].position` are the valid inputs to `/explain`'s `positions`.
   - Generation runs via OpenRouter against the same base model the NLA was trained on.

3. **`POST /api/nla/explain`**
   - Body: `{ modelId, nlaSourceId, text (the full_text) OR messages, positions:[int], temperature }`
   - Returns: `{ results:[{ position, token, description }], layer_index, prompt_length, cacheId? }`
   - **HARD LIMIT: at most 16 *new* (uncached) positions per request** (`MAX_TOKENS_TO_EXPLAIN`).
     Already-cached positions for the same `(text, modelId, nlaSourceId, temperature)` are free.
   - `description` = the Activation Verbalizer's natural-language explanation of that token's activation.

### Key modeling note
NLA "features" are **per-token-position activation descriptions**, NOT weighted SAE features.
So the attribution graph is `prompt → {one node per explained token position} → response`, each
feature node carrying the verbalizer `description`. There is no attribution weight from the API;
edges carry a placeholder/derived weight so the graph satisfies the project's ontology constraint
(every edge must have a weight attribute).

## Attribution graphs (Circuit Tracer) — the causal "how the answer formed" graph

Distinct from NLA: NLA `/explain` *describes* each token; the Circuit Tracer produces the real
causal attribution graph (feature nodes + attribution-weighted links to the output logits).
- `POST /api/graph/generate` — body `{prompt, modelId:"gemma-2-2b", slug (unique, [a-z0-9_-])}`.
  Optional thresholds (nodeThreshold, edgeThreshold, maxNLogits, maxFeatureNodes…). **gemma-2-2b
  only**, **prompt ≤ 64 tokens**, GPU-backed (slow, can 503 "GPUs busy"). Rate limit 30/hr.
  Returns `{message, s3url (graph JSON), url (interactive viewer), numNodes, numLinks}`.
  Verified 2026-05-21: ~5s, 1088 nodes / 54k links for "The capital of France is".
- The viewer `url` (`/gemma-2-2b/graph?slug=…`) has **no X-Frame-Options/CSP**, so it embeds in an
  iframe (`st.components.v1.iframe`). It logs a harmless internal React warning when embedded.
- Graph JSON is the `CLTGraph` / `ATTRIBUTION_GRAPH_SCHEMA` format (nodes, links, metadata).

### CLTGraph JSON shape (for custom rendering / the mise-en-abîme scene)
The `s3url` from `/api/graph/generate` returns a `CLTGraph` (~4.5 MB for a 6-token prompt):
- `metadata.prompt_tokens` — the gemma-2-2b tokenization.
- `nodes[]`: `node_id`, `feature`, `layer` (`"E"` for embeddings, `"0".."27"` for transcoder layers,
  last layer for logits), `ctx_idx` (token position), `feature_type`
  (`embedding` | `cross layer transcoder` | `logit` | `mlp reconstruction error`),
  `influence` (0..1, null for logits), `clerp` (label — empty for fresh transcoder nodes;
  logits carry `Output " x" (p=…)`), `token_prob`, `is_target_logit`.
- `links[]`: `source`, `target` (both `node_id`; embeddings use `E_*` ids), `weight` (signed).
- Prune for display: top ~40 transcoder nodes by `influence` + all embeddings + top logits; keep links
  among kept nodes (top by |weight|). `neuronpedia_client.fetch_attribution_subgraph` does this.
- Cross-model token→word mapping (NLA gemma-3-27b vs attribution gemma-2-2b) is done by reconstructing
  char offsets from concatenated token strings — see `_map_tokens_to_words` (approximate by design).

### Other limits (from `lib/nla-constants.ts`)
- `MAX_TEXT_LENGTH = 16384` chars, `MAX_COMPLETION_TOKENS = 512`.

### Live verification (2026-05-21)
- `GET /api/nla/sources` → 2 sources: `gemma-3-27b-it`/`kitft-l41` (layer 41) and
  `llama3.3-70b-it`/`kitft-l53` (layer 53). Both `openRouterAvailable: true`.
- `POST /api/nla/explain` with `messages` works key-less. Returns per-position
  `{ token, token_id, position, l2_norm, mse, cosine_similarity, description, ... }`
  plus top-level `layer_index`, `prompt_length`, `cacheId`. Asking for only some positions still
  returns the correct `prompt_length`, so we can probe length with a cheap 1-position call.
- `/api/nla/explain` and `/api/nla/completion` **only accept `user`/`assistant` roles** in
  `messages`. A `system` role yields HTTP 400 `"Provide either text or messages."` (the server's
  `isChatMessageArray` rejects it). To include a system/knowledge layer, fold it into the user turn
  as a context preamble (the client does `f"{system}\n\n{prompt}"`).
- To verbalize EVERY token, batch positions `[0..15], [16..31], …`: each request must have ≤16 NEW
  positions, but the server caches by position so re-covered positions are free. The client loops
  until all positions (up to a `max_tokens` cap) are covered, keeping partial results on failure.
- `POST /api/nla/completion` currently returns **HTTP 500 with empty body** for `gemma-3-27b-it`
  (server-side OpenRouter generation issue, not a client bug). The client therefore treats
  completion as **best-effort**: if it 500s we fall back to introspecting the prompt tokens via
  `/explain` with `messages`. Re-test periodically; when it recovers we also get the response text.
