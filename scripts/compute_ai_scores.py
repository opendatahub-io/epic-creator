#!/usr/bin/env python3
"""Compute AI implementability scores from individual signal values.

Reads ai_signals from epic frontmatter, sums them, applies thresholds,
and writes ai_implementability + ai_implementability_score back.

Thresholds:
    score >= 3  → High
    0 <= score <= 2 → Medium
    score <= -1 → Low

Usage:
    python3 scripts/compute_ai_scores.py RHAISTRAT-1234 RHAISTRAT-1235
    python3 scripts/compute_ai_scores.py --all
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from artifact_utils import read_frontmatter, update_frontmatter

SIGNAL_FIELDS = [
    "change_specificity",
    "pattern_precedent",
    "adapter_pattern",
    "existing_foundation",
    "open_questions",
    "external_dependency",
    "human_process_gates",
    "repo_access",
    "architecture_claims",
]


def classify(score):
    if score >= 3:
        return "High"
    elif score >= 0:
        return "Medium"
    else:
        return "Low"


def compute_for_epic(epic_path):
    """Compute and write score for a single epic file.

    Returns (epic_id, score, classification) on success, or None if
    the epic has no ai_signals.
    """
    data, _ = read_frontmatter(epic_path)
    if not data:
        return None

    signals = data.get("ai_signals")
    if not signals or not isinstance(signals, dict):
        return None

    total = 0
    for field in SIGNAL_FIELDS:
        val = signals.get(field, 0)
        if val is None:
            val = 0
        total += val

    classification = classify(total)
    epic_id = data.get("epic_id", os.path.basename(epic_path))

    old_score = data.get("ai_implementability_score")
    old_class = data.get("ai_implementability")

    if old_score != total or old_class != classification:
        update_frontmatter(epic_path, {
            "ai_implementability_score": total,
            "ai_implementability": classification,
        }, "epic-task")
        changed = " (updated)"
    else:
        changed = ""

    return epic_id, total, classification, changed


def compute_for_strategy(strat_id):
    """Compute scores for all epics of a strategy. Returns count of epics processed."""
    pattern = f"artifacts/epic-tasks/{strat_id}-E*.md"
    epic_files = sorted(glob.glob(pattern))

    if not epic_files:
        print(f"  {strat_id}: no epic files found", file=sys.stderr)
        return 0

    count = 0
    for path in epic_files:
        result = compute_for_epic(path)
        if result:
            epic_id, score, classification, changed = result
            print(f"  {epic_id}: {score} ({classification}){changed}",
                  file=sys.stderr)
            count += 1
        else:
            print(f"  {os.path.basename(path)}: no ai_signals, skipped",
                  file=sys.stderr)

    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: compute_ai_scores.py [--all | STRAT-ID ...]",
              file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--all":
        epic_files = sorted(glob.glob("artifacts/epic-tasks/*-E*.md"))
        strat_ids = set()
        for path in epic_files:
            basename = os.path.basename(path)
            parts = basename.rsplit("-E", 1)
            if len(parts) == 2:
                strat_ids.add(parts[0])
        strat_ids = sorted(strat_ids)
    else:
        strat_ids = sys.argv[1:]

    total = 0
    for strat_id in strat_ids:
        print(f"Computing scores for {strat_id}:", file=sys.stderr)
        total += compute_for_strategy(strat_id)

    print(f"Computed scores for {total} epics across "
          f"{len(strat_ids)} strategies", file=sys.stderr)


if __name__ == "__main__":
    main()
