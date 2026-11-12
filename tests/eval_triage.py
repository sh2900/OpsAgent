
"""
Run using: python -m tests.eval_triage

The evaluation saves successful predictions after every ticket.
If an LLM request fails, it stops and can resume later.
"""

import json
import time
from pathlib import Path

from agents.triage import run_triage, FALLBACK_MARKER


DATA = Path("data/triage_eval.json")
CACHE = Path("data/triage_eval_results.json")


# ---------- Load dataset and previous results ----------

with DATA.open("r", encoding="utf-8") as f:
    dataset = json.load(f)

if CACHE.exists():
    with CACHE.open("r", encoding="utf-8") as f:
        results = json.load(f)
else:
    results = {}


# ---------- Evaluate tickets ----------

for i, row in enumerate(dataset):

    key = str(i)

    # Skip tickets that already have successful results.
    if key in results:
        continue

    start = time.perf_counter()

    pred = run_triage(row["text"])

    latency = time.perf_counter() - start

    # Stop immediately if the LLM failed.
    # Fallback responses are NOT counted as predictions.
    if FALLBACK_MARKER in pred.reasoning:
        print(
            f"\nStopped at ticket {i + 1}: "
            f"LLM call failed ({pred.reasoning[:120]})."
        )
        print("Successful progress has been saved.")
        print("Fix the issue and run again to resume.")
        break

    # Store only genuine model predictions.
    results[key] = {
        "pred_category": pred.category,
        "pred_urgency": pred.urgency,
        "reasoning": pred.reasoning,
        "seconds": round(latency, 2),
    }

    # Save progress after every successful ticket.
    temp_cache = CACHE.with_suffix(".tmp")

    with temp_cache.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    temp_cache.replace(CACHE)

    print(
        f"[{i + 1}/{len(dataset)}] "
        f"{row['category']:8} -> {pred.category:8} "
        f"{row['urgency']:6} -> {pred.urgency}"
    )

    # Avoid excessive request rates.
    time.sleep(2)


# ---------- Calculate evaluation results ----------

done = [
    (dataset[int(key)], value)
    for key, value in sorted(
        results.items(),
        key=lambda item: int(item[0])
    )
]

n = len(done)

print("\n========== TRIAGE EVALUATION RESULTS ==========")

print(f"\nSuccessfully evaluated: {n}/{len(dataset)} tickets")

if n > 0:

    cat_ok = sum(
        row["category"] == result["pred_category"]
        for row, result in done
    )

    urg_ok = sum(
        row["urgency"] == result["pred_urgency"]
        for row, result in done
    )

    avg_latency = sum(
        result["seconds"]
        for _, result in done
    ) / n

    print(
        f"Category accuracy: {cat_ok}/{n} "
        f"= {cat_ok / n:.1%}"
    )

    print(
        f"Urgency accuracy: {urg_ok}/{n} "
        f"= {urg_ok / n:.1%}"
    )

    print(f"Average latency: {avg_latency:.2f}s")

    print("\nMisclassified tickets:")

    for row, result in done:

        category_wrong = (
            row["category"] != result["pred_category"]
        )

        urgency_wrong = (
            row["urgency"] != result["pred_urgency"]
        )

        if category_wrong or urgency_wrong:
            print(
                f"\nTicket: {row['text']}"
                f"\nExpected: {row['category']}/{row['urgency']}"
                f"\nPredicted: "
                f"{result['pred_category']}/{result['pred_urgency']}"
                f"\nReasoning: {result['reasoning']}"
            )

else:
    print("No successful LLM predictions available yet.")
