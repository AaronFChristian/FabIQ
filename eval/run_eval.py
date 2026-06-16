"""FabIQ evaluation runner."""
from __future__ import annotations
import argparse, asyncio, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval.golden_dataset import GOLDEN_DATASET, GoldenItem, get_tier


def _keyword_hit_rate(answer: str, keywords: list[str]) -> float:
    if not keywords: return 1.0
    lower = answer.lower()
    return round(sum(1 for kw in keywords if kw.lower() in lower) / len(keywords), 3)


async def run_single(item: GoldenItem, pipeline) -> dict:
    t0 = time.perf_counter()
    initial = {"query": item.question, "user_role": item.role,
               "session_id": item.id, "latency_ms": {}, "errors": []}
    try:
        final = await pipeline.ainvoke(initial)
        answer = final.get("response", "")
        return {"id": item.id, "tier": item.tier, "question": item.question,
                "answer": answer, "citations": final.get("citations", []),
                "eval_accuracy": final.get("eval_accuracy", 0.0),
                "eval_grounding": final.get("eval_grounding", 0.0),
                "eval_completeness": final.get("eval_completeness", 0.0),
                "eval_confidence": final.get("eval_confidence", 0.0),
                "requires_human_review": final.get("requires_human_review", False),
                "keyword_hit_rate": _keyword_hit_rate(answer, item.expected_keywords),
                "latency_ms": final.get("latency_ms", {}),
                "errors": final.get("errors", [])}
    except Exception as exc:
        return {"id": item.id, "tier": item.tier, "question": item.question,
                "answer": "", "citations": [], "eval_accuracy": 0.0, "eval_grounding": 0.0,
                "eval_completeness": 0.0, "eval_confidence": 0.0, "requires_human_review": True,
                "keyword_hit_rate": 0.0, "latency_ms": {}, "errors": [str(exc)]}


def _print_summary(results: list[dict]) -> None:
    print("\n" + "="*55)
    print("FabIQ Evaluation Summary")
    print("="*55)
    for tier in [1,2,3]:
        tr = [r for r in results if r["tier"]==tier]
        label = {1:"Factual",2:"Procedural",3:"Multi-hop"}[tier]
        avg = lambda k: sum(r[k] for r in tr)/len(tr)
        hitl = sum(1 for r in tr if r["requires_human_review"])
        print(f"\nTier {tier} — {label} ({len(tr)} questions):")
        print(f"  Accuracy:     {avg('eval_accuracy'):.2f}")
        print(f"  Grounding:    {avg('eval_grounding'):.2f}")
        print(f"  Completeness: {avg('eval_completeness'):.2f}")
        print(f"  Confidence:   {avg('eval_confidence'):.2f}")
        print(f"  Keyword hit:  {avg('keyword_hit_rate'):.2f}")
        print(f"  HITL:         {hitl}/{len(tr)}")
    overall_conf = sum(r["eval_confidence"] for r in results)/len(results)
    hitl_total = sum(1 for r in results if r["requires_human_review"])
    print(f"\nOverall: {len(results)} questions | avg confidence: {overall_conf:.2f} | HITL: {hitl_total}/{len(results)}")
    print("="*55 + "\n")


async def main(args: argparse.Namespace) -> None:
    questions = GOLDEN_DATASET if args.tier==0 else get_tier(args.tier)
    print(f"FabIQ eval: {len(questions)} questions (tier={'all' if args.tier==0 else args.tier})")
    if args.dry_run:
        print("Dry run — dataset OK, no API calls.")
        for q in questions: print(f"  [{q.id}] {q.question[:65]}...")
        return
    from fabiq.pipeline.graph import compile_pipeline
    pipeline = compile_pipeline()
    results = []
    for i, item in enumerate(questions,1):
        print(f"  [{i:2d}/{len(questions)}] {item.id}  {item.question[:50]}...")
        result = await run_single(item, pipeline)
        results.append(result)
        print(f"           conf={result['eval_confidence']:.2f}  keyword_hit={result['keyword_hit_rate']:.2f}"
              + (" ⚠ HITL" if result["requires_human_review"] else ""))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for r in results: f.write(json.dumps(r)+"\n")
    print(f"\nResults → {out}")
    _print_summary(results)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, default=0)
    parser.add_argument("--out", default="eval/results.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    asyncio.run(main(parser.parse_args()))
