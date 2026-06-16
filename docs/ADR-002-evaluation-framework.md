# ADR-002: Evaluation framework for non-deterministic RAG systems

**Date:** 2024-07
**Status:** Accepted
**Authors:** FabIQ engineering
**Reviewers:** AI Enablement Lead, Client Architecture Team

---

## Context

FabIQ is a production RAG system where incorrect answers can inform manufacturing
decisions — focus calibration parameters, reticle handling procedures, safety shutdowns.
In this domain, quality is not a UX concern; it is an operational risk concern.

Traditional software testing assumes deterministic outputs: given input X, expect output Y.
LLM-based systems are non-deterministic: the same input produces different outputs across
runs, model versions, and prompt versions. This invalidates unit-test discipline as the
primary quality gate.

We need a quality framework that:
1. Catches quality regressions before they reach users
2. Provides interpretable metrics that stakeholders can reason about
3. Scales to cover the breadth of query types engineers submit
4. Operates at low enough cost to run on every code change

---

## Decision

We implement a three-layer evaluation framework:

### Layer 1 — Lexical regression tests (fast, cheap, always-on)
The golden dataset (`eval/golden_dataset.py`) contains 30 Q&A pairs across three tiers
(factual, procedural, multi-hop), each with `expected_keywords`. The eval runner computes
a keyword hit rate per question. This catches catastrophic regressions — prompt changes
that cause the model to stop answering in the expected domain vocabulary — in under 10
seconds without any API calls.

### Layer 2 — LLM-as-judge eval (accurate, moderate cost)
Every response is scored on three dimensions by Anthropic Claude (a separate model from
the generator, reducing systematic blind spots):

| Dimension    | Definition                                                    | Production threshold |
|--------------|---------------------------------------------------------------|----------------------|
| Accuracy     | Is the answer factually correct based on retrieved sources?   | ≥ 0.75               |
| Grounding    | Does every claim trace back to a cited source?                | ≥ 0.80               |
| Completeness | Does the answer fully address the question?                   | ≥ 0.70               |
| **Confidence** | Mean of the three dimensions                               | **≥ 0.60 for auto-return** |

If aggregate confidence falls below 0.60, the response is routed to a human review queue
(HITL gate) rather than returned automatically. This is enforced in Agent 5 of the pipeline.

### Layer 3 — Human-in-the-loop review queue (ground truth, low volume)
Responses flagged by the HITL gate are reviewed by a domain expert (process engineer or
AI Enablement team member). Reviewed responses — with corrections — feed back into the
golden dataset, continuously improving regression coverage.

---

## Why LLM-as-judge rather than human evaluation for every response?

Human evaluation is the gold standard but does not scale: at 125 wafers/hour and multiple
engineers per shift, query volume makes per-response human review impractical. LLM-as-judge
at Claude Sonnet quality has been shown to correlate strongly with human judgment on RAG
quality tasks when the judge is given explicit scoring criteria and access to source documents.

The key design choice is **using a different model as judge than as generator**. This reduces
the risk that both models share the same systematic biases — a weakness in self-evaluation
approaches. Azure OpenAI GPT-4o generates; Anthropic Claude evaluates.

---

## Why a golden dataset rather than sampling production queries?

Production queries may contain PII, proprietary technical parameters, or reference
documents we cannot redistribute. A curated golden dataset:
- Is fully controllable (we can update it as the system evolves)
- Covers corner cases deliberately (multi-hop questions are underrepresented in early
  production traffic but are the hardest failure mode)
- Has known reference answers for calibration

The 30-question dataset is intentionally small for Day 1 — it is designed to grow to
200+ questions through the Layer 3 human review feedback loop.

---

## Cost model

| Layer | Cost per eval run | Latency |
|-------|------------------|---------|
| Layer 1 (lexical) | $0.00 | < 1 second |
| Layer 2 (LLM judge, 30 questions) | ~$0.15 at current Claude Sonnet pricing | ~45 seconds |
| Layer 3 (human review) | ~15 min engineer time per flagged response | async |

At the current HITL trigger rate (estimated 10-15% of queries in pre-production testing),
human review volume is manageable. As the golden dataset grows and prompts stabilise,
the expected HITL rate drops.

---

## Consequences

### Positive
- Non-deterministic system quality is now measurable and trackable across deployments
- Every prompt change is testable before promotion: run eval suite on v1.x, compare to v1.0 baseline
- The HITL gate provides a hard safety boundary: low-confidence answers never auto-return
- Evaluation results are logged to LangSmith, enabling quality trend analysis over time

### Negative / Risks
- LLM-as-judge introduces a second model call per production query (~$0.005 per query at
  current pricing). This is justified by the risk profile but should be tracked in cost dashboards.
- Judge calibration: Claude Sonnet's scoring is not perfectly calibrated to this domain. Initial
  calibration against human-reviewed responses is required (tracked in Layer 3 feedback loop).
- The 0.60 HITL threshold was set conservatively. It should be tuned against production data
  after the first 500 queries and reviewed quarterly.

### Out of scope for this ADR
- A/B testing framework for comparing prompt versions on live traffic (planned Q4)
- Automated threshold tuning via calibration against human labels (planned Q1 next year)

---

## References

- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023)
- LangSmith documentation: evaluation and feedback
- Internal: FabIQ ADR-001 — Chunking strategy selection
