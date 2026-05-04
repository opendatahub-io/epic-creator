"""Phase-aware progress checker for agent polling.

Reports completion status for a list of strategy IDs based on the current phase.
Supports ``--wait`` mode which sleeps internally so the caller does not need
to parse ``NEXT_POLL`` values.
"""

import argparse
import os
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from artifact_utils import read_frontmatter


PHASE_CHECKS = {
    "fetch": lambda id: f"artifacts/strat-tasks/{id}.md",
    "decompose": lambda id: f"artifacts/epic-tasks/{id}-decomposition.md",
    "review_decomp": lambda id: f"artifacts/epic-reviews/{id}-decomp-review.md",
    "revise_decomp": lambda id: f"artifacts/epic-tasks/{id}-decomposition.md",
}


def check_id(phase, strat_id):
    """Check one ID. Returns 'completed', 'pending', or 'error'."""
    path = PHASE_CHECKS[phase](strat_id)
    if not os.path.exists(path):
        return "pending"
    if phase == "review_decomp":
        try:
            data, _ = read_frontmatter(path)
        except Exception:
            return "error"
        if not data:
            return "error"
        if data.get("score") is None:
            return "pending"
        if data.get("error"):
            return "error"
    if phase == "revise_decomp":
        try:
            data, _ = read_frontmatter(path)
        except Exception:
            return "error"
        if not data:
            return "error"
        if data.get("revised"):
            return "completed"
        return "pending"
    return "completed"


def _check_phase(phase, ids, fast):
    """Check one phase and return (completed, errors, pending, total, next_poll)."""
    completed = 0
    errors = 0
    pending_ids = []

    for strat_id in ids:
        result = check_id(phase, strat_id)
        if result == "completed":
            completed += 1
        elif result == "error":
            errors += 1
        else:
            pending_ids.append(strat_id)

    total = len(ids)
    pending = len(pending_ids)

    if pending == 0:
        next_poll = 0
    elif fast:
        next_poll = 15
    elif completed / total >= 0.75:
        next_poll = 15
    elif completed / total >= 0.5:
        next_poll = 30
    else:
        next_poll = 60

    return completed, errors, pending, total, next_poll


def _format_status(phase, completed, errors, pending, total, next_poll):
    """Format a status line for one phase."""
    parts = [f"COMPLETED={completed}/{total}"]
    if pending:
        parts.append(f"PENDING={pending}")
    if errors:
        parts.append(f"ERRORS={errors}")
    parts.append(f"NEXT_POLL={next_poll}")
    return f"{phase}: {', '.join(parts)}"


def _detect_fast(explicit_flag):
    """Return True if fast-poll should be used."""
    if explicit_flag:
        return True
    for cfg in ("tmp/decompose-config.yaml", "tmp/pipeline-state.yaml"):
        if os.path.exists(cfg):
            try:
                with open(cfg) as f:
                    data = yaml.safe_load(f)
                if data and data.get("headless") is False:
                    return True
            except Exception:
                pass
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Check decomposition pipeline progress by phase")
    parser.add_argument("--phase", required=True,
                        choices=list(PHASE_CHECKS.keys()),
                        help="Pipeline phase to check")
    parser.add_argument("--also-phase", action="append",
                        dest="also_phases",
                        choices=list(PHASE_CHECKS.keys()),
                        help="Additional phases to check (wait mode)")
    parser.add_argument("--id-file",
                        help="File containing IDs (one per line or "
                             "space-separated)")
    parser.add_argument("--fast-poll", action="store_true",
                        help="Cap poll interval at 15s (interactive mode). "
                             "Auto-enabled when config files show headless=false.")
    parser.add_argument("--wait", action="store_true",
                        help="Block until all agents complete, sleeping "
                             "internally between checks. Exit 0 when done.")
    parser.add_argument("--max-wait", type=int, default=90,
                        help="Max seconds to wait in --wait mode before timing out (exit 3). "
                             "Default 90 (fits within 2-min bash timeout).")
    parser.add_argument("ids", nargs="*", metavar="ID",
                        help="Strategy IDs to check")
    args = parser.parse_args()

    ids = args.ids
    if args.id_file:
        with open(args.id_file) as f:
            ids = f.read().split()
    if not ids:
        print("No IDs provided", file=sys.stderr)
        sys.exit(2)

    fast = _detect_fast(args.fast_poll)
    phases = [args.phase] + (args.also_phases or [])

    if args.max_wait < 0:
        parser.error("--max-wait must be non-negative")

    if args.wait:
        start = time.monotonic()
        while True:
            all_complete = True
            max_poll = 0
            for phase in phases:
                completed, errors, pending, total, next_poll = \
                    _check_phase(phase, ids, fast)
                print(_format_status(
                    phase, completed, errors, pending, total, next_poll),
                    flush=True)
                if pending > 0:
                    all_complete = False
                max_poll = max(max_poll, next_poll)

            if all_complete:
                if len(phases) > 1:
                    print("All phases complete.")
                break

            elapsed = time.monotonic() - start
            if args.max_wait > 0 and (elapsed + max_poll) > args.max_wait:
                pending_ids = set()
                for phase in phases:
                    for strat_id in ids:
                        if check_id(phase, strat_id) == "pending":
                            pending_ids.add(strat_id)
                id_list = sorted(pending_ids)
                if len(id_list) > 5:
                    id_summary = ' '.join(id_list[:5]) + f' ... and {len(id_list) - 5} more'
                else:
                    id_summary = ' '.join(id_list)
                print(f"Waited {int(elapsed)}s, still pending: "
                      f"{id_summary}. "
                      f"Re-run this command.", flush=True)
                sys.exit(3)

            print(f"Sleeping {max_poll}s...", flush=True)
            time.sleep(max_poll)
    else:
        completed, errors, pending, total, next_poll = \
            _check_phase(args.phase, ids, fast)
        parts = [f"COMPLETED={completed}/{total}"]
        if pending:
            parts.append(f"PENDING={pending}")
        if errors:
            parts.append(f"ERRORS={errors}")
        parts.append(f"NEXT_POLL={next_poll}")
        print(", ".join(parts))


if __name__ == "__main__":
    main()
