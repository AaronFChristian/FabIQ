# FabIQ

**Production multi-agent RAG system for technical documentation intelligence**

Built to demonstrate production AI engineering discipline for the ASML AI Engineer role —
covering every requirement in the JD: end-to-end RAG, multi-agent LangGraph orchestration,
privilege-aware retrieval, LLM-as-judge evaluation, LangSmith observability, prompt versioning,
and a complete operational runbook.

---

## What it does

Engineers at semiconductor manufacturers spend 2–3 hours per shift searching thousands of
pages of machine manuals, fab process specs, and compliance guidelines to answer precise
technical questions. A wrong answer can stop a production line. FabIQ solves this with a
5-agent pipeline that retrieves with role-based access control, grounds every answer in
citations, and continuously measures its own quality.

---

## Architecture

```
User query
  → Agent 1: Query understanding  — classifies intent, rewrites for retrieval
  → Agent 2: Privilege check      — maps role → access filter (server-side RBAC)
  → Agent 3: Hybrid retrieval     — vector + BM25 via Azure AI Search
  → Agent 4: Citation grounding   — GPT-4o generates answer, every claim cited
  → Agent 5: LLM-as-judge eval    — Claude scores accuracy / grounding / completeness
  → HITL gate                     — if confidence < 0.60, routes to human review
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| LLM (generation) | Azure OpenAI GPT-4o |
| LLM (evaluation) | Anthropic Claude Sonnet — separate judge model |
| Vector store | Azure AI Search (hybrid vector + BM25) |
| Orchestration | LangGraph 5-agent state machine |
| Observability | LangSmith — every agent call traced |
| API | FastAPI (async, streaming, Pydantic v2) |
| Dashboard | Streamlit — query UI + live metrics |
| Prompt versioning | JSON config with version registry |
| CI/CD | GitHub Actions (lint → test → docker build → eval regression) |
| Containers | Docker multi-stage + docker-compose |

---

## Project structure

```
fabiq/
├── src/fabiq/
│   ├── agents/          # 5 LangGraph agents
│   ├── pipeline/        # graph.py + prompt_registry.py + prompts.json
│   ├── ingestion/       # loader, chunker (3 strategies), embedder
│   ├── retrieval/       # Azure AI Search hybrid search + RBAC filter
│   ├── api/             # FastAPI routes (/ingest, /query, /health)
│   └── observability/   # LangSmith tracing
├── dashboard/           # Streamlit observability dashboard
├── eval/                # Golden dataset (30 Q&A) + eval runner
├── tests/               # 65 passing tests (Day 1 + Day 2 coverage)
├── docs/
│   ├── ADR-001-chunking-strategy.md
│   ├── ADR-002-evaluation-framework.md
│   └── RUNBOOK.md
├── .github/workflows/   # CI pipeline
├── Dockerfile
└── docker-compose.yml
```

---

## Quickstart

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/fabiq.git && cd fabiq
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure Azure credentials
cp .env.example .env
# Fill in AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
#         AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY
# Optional: ANTHROPIC_KEY (LLM-as-judge), LANGSMITH_API_KEY (tracing)

# 3. Run tests (no Azure needed)
PYTHONPATH=src:. pytest tests/ -v --no-cov    # → 65 passed

# 4. Validate eval dataset
PYTHONPATH=src:. python eval/run_eval.py --dry-run    # → 30 questions listed

# 5. Start the server
PYTHONPATH=src uvicorn fabiq.api.main:app --reload --port 8000

# 6. Start the dashboard
PYTHONPATH=src streamlit run dashboard/app.py

# 7. Run full eval (requires Azure + Anthropic credentials)
PYTHONPATH=src:. python eval/run_eval.py
```

---

## Key design decisions

See `docs/ADR-001-chunking-strategy.md` — why recursive is the default over fixed or semantic.

See `docs/ADR-002-evaluation-framework.md` — why LLM-as-judge + golden dataset rather than
human evaluation for every response; HITL threshold justification; cost model.

See `docs/RUNBOOK.md` — how to update a prompt safely, run eval regression, monitor in
production, and handle incidents.

---

## Evaluation

The 30-question golden dataset spans three tiers:
- **Tier 1** (10 questions): Factual lookups — single-source, specific answers
- **Tier 2** (10 questions): Procedural — step-based how-to questions
- **Tier 3** (10 questions): Multi-hop — require reasoning across multiple documents

Each question has expected keywords for lightweight lexical regression plus reference answers
for the LLM-as-judge eval. Results are written to `eval/results.jsonl` with per-question
scores for trend analysis.

---

## Tests

```
65 passing tests covering:
  ├── 21 chunker tests   (fixed, recursive, semantic strategies)
  ├── 17 loader tests    (PDF, markdown, directory loading, RBAC metadata)
  ├── 7  search tests    (RBAC filter logic, OData syntax, SearchResult)
  ├── 13 agent tests     (all 5 agents with mocked Azure/Anthropic clients)
  └── 7  pipeline tests  (graph compilation, HITL routing, golden dataset)
```

---

## Published research

LLM2Manim — arXiv preprint on converting natural-language STEM questions to animated
visual explanations via LLM pipelines. Demonstrates prior production AI engineering work.

---

*Built in 72 hours as a portfolio project demonstrating production AI engineering for the
ASML AI Engineer role. Not affiliated with ASML or UTIS LLC.*

---

## Deployment modes: Azure production + local reviewer mode

FabIQ supports two execution modes so the Azure implementation can remain intact while reviewers can still run the project without cloud credentials.

### 1. Azure production mode

This is the intended production architecture:

- Azure OpenAI for embeddings and chat generation
- Azure AI Search for hybrid retrieval and RBAC filtering
- LangGraph for the 5-agent orchestration pipeline
- Optional Anthropic judge for evaluation
- Optional LangSmith tracing

Use this mode when Azure credentials and model quota are available:

```env
APP_MODE=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=...
AZURE_SEARCH_INDEX_NAME=fabiq-docs
```

### 2. Local reviewer/demo mode

This mode does **not** require Azure login, Azure quota, Azure OpenAI, or Azure AI Search.

It demonstrates the core system flow:

- document upload
- chunking
- local embeddings
- local vector retrieval
- role-based access filtering
- citation formatting
- FastAPI routes
- dashboard integration

Local mode intentionally uses extractive/template-based answer generation instead of a cloud LLM. Full generative answer quality is available in Azure mode.

```env
APP_MODE=local
LOCAL_INDEX_PATH=data/local_index.json
LOCAL_EMBEDDING_MODEL=hash
```

Optional: set `LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2` for stronger local semantic retrieval if the model is installed/cached locally.

### Run locally without Azure

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# keep APP_MODE=local
PYTHONPATH=src uvicorn fabiq.api.main:app --reload --port 8000
```

Check health:

```bash
curl http://localhost:8000/health
```

Ingest the included sample document:

```bash
curl -X POST "http://localhost:8000/ingest/" \
  -F "file=@sample_data/local_demo.md" \
  -F "access_level=public" \
  -F "chunk_strategy=recursive"
```

Query the local index:

```bash
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query":"What does local demo mode demonstrate?","role":"field_engineer"}'
```

### Why local mode exists

FabIQ was implemented with Azure resources as the primary cloud architecture. Student/free Azure subscriptions can expire, lose quota, or restrict model deployment by region. Local mode allows reviewers to verify that the ingestion, retrieval, RBAC, citation, API, and dashboard workflow still runs without needing the author's Azure credentials.
