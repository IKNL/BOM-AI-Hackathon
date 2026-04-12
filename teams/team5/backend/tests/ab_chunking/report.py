"""Format AB test results into readable reports."""

import json
from tests.ab_chunking.metrics import compare_to_baseline


def format_report(results: list[dict], source: str) -> str:
    """Format results into a markdown report."""
    lines = [f"# AB Test Results: {source}", ""]

    # Aggregate table
    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append("| Variant | Chunks | Avg Words | Recall@5 | Precision@5 | MRR | vs Baseline |")
    lines.append("|---------|--------|-----------|----------|-------------|-----|-------------|")

    baseline_agg = results[0]["aggregate"] if results else {}

    for r in results:
        agg = r["aggregate"]
        delta = compare_to_baseline(baseline_agg, agg) if r != results[0] else {}
        delta_str = " / ".join(
            f"{v:+.1f}%" for k, v in delta.items()
        ) if delta else "—"

        lines.append(
            f"| {r['variant']} | {r['chunk_count']} | {r['avg_chunk_words']} | "
            f"{agg['recall_at_5']:.3f} | {agg['precision_at_5']:.3f} | "
            f"{agg['mrr']:.3f} | {delta_str} |"
        )

    # Per-category breakdown
    lines.append("")
    lines.append("## Per-Category Breakdown")
    categories = sorted(set(q["category"] for r in results for q in r["per_query"]))

    for cat in categories:
        lines.append(f"\n### {cat.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Variant | Recall@5 | Precision@5 | MRR |")
        lines.append("|---------|----------|-------------|-----|")

        for r in results:
            cat_queries = [q for q in r["per_query"] if q["category"] == cat]
            if not cat_queries:
                continue
            n = len(cat_queries)
            avg_r = sum(q["recall_at_5"] for q in cat_queries) / n
            avg_p = sum(q["precision_at_5"] for q in cat_queries) / n
            avg_m = sum(q["mrr"] for q in cat_queries) / n
            lines.append(f"| {r['variant']} | {avg_r:.3f} | {avg_p:.3f} | {avg_m:.3f} |")

    # Decision
    lines.append("")
    lines.append("## Decision")
    lines.append("")

    best = max(results, key=lambda r: r["aggregate"]["recall_at_5"] + r["aggregate"]["mrr"])
    baseline = results[0]
    delta = compare_to_baseline(baseline["aggregate"], best["aggregate"])
    r5_delta = delta.get("recall_at_5_delta_pct", 0)
    mrr_delta = delta.get("mrr_delta_pct", 0)

    if best == baseline:
        lines.append("**Result: Baseline wins.** No alternative improved on both Recall@5 and MRR.")
    elif r5_delta > 5 and mrr_delta > 5:
        lines.append(f"**Result: SHIP `{best['variant']}`** -- "
                     f"Recall@5 +{r5_delta:.1f}%, MRR +{mrr_delta:.1f}% over baseline.")
    elif r5_delta > 5 or mrr_delta > 5:
        lines.append(f"**Result: DRILL DOWN on `{best['variant']}`** -- "
                     f"Partial improvement (R@5 {r5_delta:+.1f}%, MRR {mrr_delta:+.1f}%). "
                     f"Test sub-variants with tuned parameters.")
    else:
        lines.append("**Result: INCONCLUSIVE** -- All variants within 5% of baseline. Ship simplest option.")

    return "\n".join(lines)


def save_results(results: list[dict], source: str, output_dir: str) -> tuple[str, str]:
    """Save raw JSON results and markdown report."""
    from pathlib import Path
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / f"{source}_results.json"
    md_path = out / f"{source}_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    report = format_report(results, source)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)

    return str(json_path), str(md_path)
