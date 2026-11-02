
"""Run using: python -m tests.eval_triage"""

import json
import time

from agents.triage import run_triage


# Load the evaluation dataset
with open("data/triage_eval.json", encoding="utf-8") as f:
    dataset = json.load(f)


cat_ok = 0
urg_ok = 0
misses = []
latencies = []
fallbacks = 0


# Evaluate every ticket
for i, row in enumerate(dataset, 1):

    start = time.perf_counter()

    pred = run_triage(row["text"])

    latency = time.perf_counter() - start
    latencies.append(latency)

    # Compare predicted category and urgency
    category_correct = pred.category == row["category"]
    urgency_correct = pred.urgency == row["urgency"]

    cat_ok += category_correct
    urg_ok += urgency_correct

    # Count fallback responses independently
    if "Automatic triage failed" in pred.reasoning:
        fallbacks += 1

    # Store incorrect predictions
    if not category_correct or not urgency_correct:
        misses.append((row, pred))

    print(
        f"[{i}/{len(dataset)}] "
        f"{row['category']:8} -> {pred.category:8} "
        f"{row['urgency']:6} -> {pred.urgency}"
    )

    # Avoid exceeding free-tier request rates
    time.sleep(1.5)


# Calculate final metrics
n = len(dataset)

print("\n========== TRIAGE EVALUATION RESULTS ==========")

print(
    f"\nCategory accuracy: {cat_ok}/{n} "
    f"= {cat_ok / n:.1%}"
)

print(
    f"Urgency accuracy:  {urg_ok}/{n} "
    f"= {urg_ok / n:.1%}"
)

print(
    f"Avg triage latency: "
    f"{sum(latencies) / n:.2f}s"
)

print(f"Fallbacks used: {fallbacks}")

print("\nMisclassified tickets:")

for row, pred in misses:
    print(
        f"\nTicket: {row['text']}"
        f"\nExpected: {row['category']}/{row['urgency']}"
        f"\nPredicted: {pred.category}/{pred.urgency}"
        f"\nReasoning: {pred.reasoning}"
    )
