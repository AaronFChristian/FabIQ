# FabIQ Operational Runbook

**Version:** 1.0
**Last updated:** 2024-07
**Owner:** FabIQ Engineering
**Audience:** AI Enablement team, on-call engineers

---

## 1. System overview

FabIQ is a 5-agent LangGraph RAG pipeline that answers technical questions from indexed
engineering documentation. It exposes a FastAPI REST service and a Streamlit dashboard.

```
User query
  → Agent 1: Query understanding     (Azure OpenAI GPT-4o)
  → Agent 2: Privilege check         (pure logic, no LLM)
  → Agent 3: Hybrid retrieval        (Azure AI Search)
  → Agent 4: Citation grounding      (Azure OpenAI GPT-4o)
  → Agent 5: LLM-as-judge eval       (Anthropic Claude Sonnet)
  → HITL gate (if confidence < 0.60) → Human review queue
  → Response returned to user
```

**Key service endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Readiness probe — returns Azure connectivity status |
| `GET /index/status` | Document count in Azure AI Search |
| `POST /ingest/` | Upload and index a document |
| `POST /query/` | Run a query through the 5-agent pipeline |

---

## 2. Starting the service

```bash
# Development (with hot reload)
PYTHONPATH=src uvicorn fabiq.api.main:app --reload --port 8000

# Dashboard
PYTHONPATH=src streamlit run dashboard/app.py

# Production (Docker)
docker compose up --build
```

**Required environment variables** (see `.env.example`):
- `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY`
- `AZURE_SEARCH_ENDPOINT` + `AZURE_SEARCH_API_KEY`
- `ANTHROPIC_KEY` (for LLM-as-judge eval; if absent, heuristic scoring is used)
- `LANGSMITH_API_KEY` (optional; tracing disabled if absent)

---

## 3. Ingesting documents

```bash
# Via curl
curl -X POST http://localhost:8000/ingest/ \
  -F "file=@manuals/euv-maintenance-guide.pdf" \
  -F "access_level=internal" \
  -F "chunk_strategy=recursive"

# Expected response
{
  "doc_id": "a3f8c2d1",
  "filename": "euv-maintenance-guide.pdf",
  "chunks_indexed": 87,
  "strategy_used": "recursive",
  "access_level": "internal",
  "elapsed_ms": 12430.5
}
```

**Chunking strategy guide:**
| Document type | Recommended strategy |
|--------------|---------------------|
| Dense prose (manuals, runbooks) | `recursive` |
| Structured tables / specs | `fixed` |
| High-value technical papers | `semantic` |

---

## 4. Updating a prompt

Prompt changes are **never made by editing code**. All prompts live in
`src/fabiq/pipeline/prompts.json` and are loaded at runtime by the prompt registry.

**Safe prompt update procedure:**

1. **Add a new version** in `prompts.json` under the relevant agent key:
   ```json
   "v1.2": {
     "system": "... your updated prompt ...",
     "temperature": 0.0,
     "max_tokens": 1024,
     "notes": "Describe what changed and why"
   }
   ```

2. **Run the eval suite against the new version**:
   ```bash
   # Temporarily set active_version to v1.2 in prompts.json
   PYTHONPATH=src:. python eval/run_eval.py --out eval/results-v1.2.jsonl
   ```

3. **Compare scores** against the v1.1 baseline:
   ```bash
   # Each line in the JSONL is one question result with eval_confidence
   # Verify avg confidence has not regressed
   python3 -c "
   import json
   results = [json.loads(l) for l in open('eval/results-v1.2.jsonl')]
   avg = sum(r['eval_confidence'] for r in results) / len(results)
   hitl = sum(1 for r in results if r['requires_human_review'])
   print(f'Avg confidence: {avg:.3f}  HITL triggered: {hitl}/30')
   "
   ```

4. **Promote if scores are equal or better**: set `"active_version": "v1.2"` in `prompts.json`.

5. **Commit and push** — the changelog entry is part of the commit.

> ⚠ Never change an existing version entry. Add new versions only. This preserves the audit trail.

---

## 5. Running eval regression

Run before every deployment that changes a prompt, model version, or retrieval config.

```bash
# Full 30-question eval (requires Azure + Anthropic credentials)
PYTHONPATH=src:. python eval/run_eval.py

# Specific tier only
PYTHONPATH=src:. python eval/run_eval.py --tier 1

# Validate dataset only (no API calls)
PYTHONPATH=src:. python eval/run_eval.py --dry-run

# Save results for comparison
PYTHONPATH=src:. python eval/run_eval.py --out eval/results-$(date +%Y%m%d).jsonl
```

**Quality gates (block deployment if breached):**
- Avg eval_confidence < 0.65
- Tier 1 (factual) avg accuracy < 0.80
- HITL trigger rate > 30%

---

## 6. Monitoring in production

**LangSmith dashboard** (if `LANGSMITH_API_KEY` is set):
- Every agent call is traced with inputs, outputs, latency, and token count
- Set up alerts for: avg latency > 10s, error rate > 2%, confidence < 0.60 for >20% of queries

**Key metrics to watch:**

| Metric | Warning threshold | Critical threshold |
|--------|------------------|-------------------|
| End-to-end latency | > 8 seconds | > 15 seconds |
| Agent 3 retrieval score | < 0.5 | < 0.3 |
| HITL trigger rate | > 20% | > 40% |
| Avg eval confidence | < 0.70 | < 0.60 |
| Token cost per query | > $0.05 | > $0.15 |

**Health check** (include in monitoring ping):
```bash
curl -s http://localhost:8000/health | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d['status']=='ok' else 1)"
```

---

## 7. Incident response

### Query returns requires_review: true
- Expected behaviour — the HITL gate is working.
- Route the question and answer to the domain expert review queue.
- If HITL rate spikes above 40% suddenly: check Azure AI Search health (`/index/status`)
  and verify index document count has not dropped (indicates accidental index deletion).

### Retrieval returns 0 results
- Verify the index exists: `GET /index/status`
- Verify the user role is correct (field_engineer cannot see internal docs)
- Re-ingest documents if the index was recreated: `POST /ingest/` for each document

### Azure OpenAI rate limit errors
- The embedder retries automatically with exponential backoff (up to 5 attempts)
- If errors persist: check Azure quota in the portal, request quota increase

### Agent 5 fails (Anthropic key missing)
- Eval judge falls back to heuristic scoring (no API call)
- Heuristic scores are conservative — HITL rate will be higher than normal
- Set `ANTHROPIC_KEY` in `.env` and restart to restore LLM-as-judge scoring

---

## 8. Deploying a new model version

When Azure OpenAI releases a new model (e.g. gpt-4o → gpt-4o-2024-11):

1. Deploy the new model in Azure OpenAI Studio under a new deployment name
2. Update `AZURE_OPENAI_CHAT_DEPLOYMENT` in `.env`
3. Run full eval regression (`python eval/run_eval.py`)
4. Compare scores to previous baseline
5. If no regression: promote to production. If regression: keep previous deployment.

> Never change the model deployment name without running eval regression first.

---

## 9. Contacts and escalation

| Issue | First contact |
|-------|--------------|
| Azure service issues | Azure support portal |
| Anthropic API issues | status.anthropic.com |
| FabIQ application bugs | fabiq-engineering team |
| Domain question accuracy | AI Enablement Lead / domain SME |
