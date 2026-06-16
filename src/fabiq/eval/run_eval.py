"""
FabIQ evaluation runner.

Runs all 30 golden-dataset questions through the LangGraph pipeline and
produces a JSONL results file + a human-readable summary report.

Usage:
    python eval/run_eval.py                    # run all 30 questions
    python eval/run_eval.py --tier 1           # run only tier-1 questions
    python eval/run_eval.py --dry-run          # validate dataset loads, no API calls
    python eval/run_eval.py --out results.jsonl

Output JSONL schema per line:
    {
      "id": "T1-01",
      "tier": 1,
      "question": "...",
      "answer": "...",
      "citations": [...],
      "eval_accuracy": 0.85,
      "eval_grounding": 0.90,
      "eval_completeness": 0.80,
      "eval_confidence": 0.85,
      "requires_human_review": false,
      "keyword_hit_rate": 1.0,
      "latency_ms": {...},
      "errors": []
    }
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Ensure src/ is on the path when run from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog
from eval.golden_dataset import GOLDEN_DATASET, GoldenItem, get_tier

log = structlog.get_logger(__name__)


def _keyword_hit_rate(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lower)
    return round(hits / len(keywords), 3)


async def run_single(item: GoldenItem, pipeline) -> dict:
    """Run one golden item through the pipeline and return a result dict."""
    t0 = time.perf_counter()
    initial_state = {
        "query":      item.question,
        "user_role":  item.role,
        "session_id": item.id,
        "latency_ms": {},
        "errors":     [],
    }

    try:
        final_state = await pipeline.ainvoke(initial_state)
        answer = final_state.get("response", "")
        khr = _keyword_hit_rate(answer, item.expected_keywords)

        return {
            "id":                   item.id,
            "tier":                 item.tier,
            "question":             item.question,
            "answer":               answer,
            "citations":            final_state.get("citations", []),
            "eval_accuracy":        final_state.get("eval_accuracy", 0.0),
            "eval_grounding":       final_state.get("eval_grounding", 0.0),
            "eval_completeness":    final_state.get("eval_completeness", 0.0),
            "eval_confidence":      final_state.get("eval_confidence", 0.0),
            "requires_human_review":final_state.get("requires_human_review", False),
            "keyword_hit_rate":     khr,
            "latency_ms":           final_state.get("latency_ms", {}),
            "errors":               final_state.get("errors", []),
        }

    except Exception as exc:
        log.error("eval_item_failed", id=item.id, error=str(exc))
        return {
            "id": item.id, "tier": item.tier, "question": item.question,
            "answer": "", "citations": [],
            "eval_accuracy": 0.0, "eval_grounding": 0.0, "eval_completeness": 0.0,
            "eval_confidence": 0.0, "requires_human_review": True,
            "keyword_hit_rate": 0.0, "latency_ms": {},
            "errors": [str(exc)],
        }


def _print_summary(results: list[dict]) -> None:
    """Print a human-readable summary table."""
    tiers = sorted({r["tier"] for r in results})
    print("\n" + "="*60)
    print("FabIQ Evaluation Summary")
    print("="*60)

    for tier in tiers:
        tier_results = [r for r in results if r["tier"] == tier]
        avg_acc  = sum(r["eval_accuracy"] for r in tier_results) / len(tier_results)
        avg_grd  = sum(r["eval_grounding"] for r in tier_results) / len(tier_results)
        avg_comp = sum(r["eval_completeness"] for r in tier_results) / len(tier_results)
        avg_conf = sum(r["eval_confidence"] for r in tier_results) / len(tier_results)
        avg_khr  = sum(r["keyword_hit_rate"] for r in tier_results) / len(tier_results)
        hitl_ct  = sum(1 for r in tier_results if r["requires_human_review"])
        errors   = sum(len(r["errors"]) for r in tier_results)

        tier_label = {1: "Factual", 2: "Procedural", 3: "Multi-hop"}[tier]
        print(f"\nTier {tier} — {tier_label} ({len(tier_results)} questions):")
        print(f"  Accuracy:        {avg_acc:.2f}")
        print(f"  Grounding:       {avg_grd:.2f}")
        print(f"  Completeness:    {avg_comp:.2f}")
        print(f"  Confidence:      {avg_conf:.2f}")
        print(f"  Keyword hit:     {avg_khr:.2f}")
        print(f"  HITL triggered:  {hitl_ct}/{len(tier_results)}")
        if errors:
            print(f"  ⚠ Errors:        {errors}")

    # Overall
    avg_conf_all = sum(r["eval_confidence"] for r in results) / len(results)
    hitl_total   = sum(1 for r in results if r["requires_human_review"])
    print(f"\nOverall: {len(results)} questions  |  avg confidence: {avg_conf_all:.2f}  |  HITL: {hitl_total}/{len(results)}")
    print("="*60 + "\n")


async def main(args: argparse.Namespace) -> None:
    questions = GOLDEN_DATASET if args.tier == 0 else get_tier(args.tier)
    print(f"Running FabIQ eval: {len(questions)} questions (tier={'all' if args.tier==0 else args.tier})")

    if args.dry_run:
        print("Dry run — dataset loaded OK, no API calls made.")
        for q in questions:
            print(f"  [{q.id}] {q.question[:70]}...")
        return

    from fabiq.pipeline.graph import compile_pipeline
    pipeline = compile_pipeline()

    results: list[dict] = []
    for i, item in enumerate(questions, 1):
        print(f"  [{i:2d}/{len(questions)}] {item.id}  {item.question[:55]}...")
        result = await run_single(item, pipeline)
        results.append(result)

        conf = result["eval_confidence"]
        khr  = result["keyword_hit_rate"]
        flag = " ⚠ HITL" if result["requires_human_review"] else ""
        print(f"           conf={conf:.2f}  keyword_hit={khr:.2f}{flag}")

    # Write JSONL
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"\nResults written to {out_path}")

    _print_summary(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FabIQ golden-dataset eval runner")
    parser.add_argument("--tier", type=int, default=0, help="0=all, 1-3=specific tier")
    parser.add_argument("--out", default="eval/results.jsonl", help="Output JSONL path")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset only, no API calls")
    asyncio.run(main(parser.parse_args()))
