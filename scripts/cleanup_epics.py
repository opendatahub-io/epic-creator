#!/usr/bin/env python3
"""Close and unlink auto-created epics for a strategy, enabling re-decomposition.

For each strategy ID provided, this script:
  1. Finds child epics with the epic-creator-auto-created label
  2. Closes each as Obsolete
  3. Removes the parent link (so the strategy's child list is clean)
  4. Removes the epic-creator-auto-decomposed label from the strategy

After cleanup, the pipeline's --skip-if-has-epics check will no longer
block re-decomposition of the strategy.

Usage:
    python scripts/cleanup_epics.py [--dry-run] RHAISTRAT-ID ...

Environment variables:
    JIRA_SERVER  Jira server URL (e.g. https://mysite.atlassian.net)
    JIRA_USER    Jira username/email
    JIRA_TOKEN   Jira API token
"""

import argparse
import re
import sys
import os
import urllib.parse

sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.dirname(__file__))
from jira_utils import (
    require_env,
    api_call_with_retry,
    get_transitions,
    do_transition,
    remove_labels,
)

AUTO_CREATED_LABEL = "epic-creator-auto-created"
STRAT_LABEL = "epic-creator-auto-decomposed"
OBSOLETE_RESOLUTION = "Obsolete"


def _find_auto_epics(server, user, token, strat_id):
    """Find child epics of a strategy that were auto-created."""
    jql = urllib.parse.quote(
        f"parent = {strat_id} AND project = RHAI "
        f"AND labels = {AUTO_CREATED_LABEL}"
    )
    result = api_call_with_retry(
        server,
        f"/search/jql?jql={jql}&fields=summary,status&maxResults=100",
        user, token,
    )
    return result.get("issues", [])


def _close_as_obsolete(server, user, token, issue_key):
    """Transition an issue to Closed with Obsolete resolution.

    Returns True on success, False if already closed or transition unavailable.
    """
    transitions = get_transitions(server, user, token, issue_key)
    close_transition = None
    for t in transitions:
        if t["to"].get("name", "").lower() == "closed":
            close_transition = t
            break
    if not close_transition:
        return False
    do_transition(
        server, user, token, issue_key, close_transition["id"],
        fields={"resolution": {"name": OBSOLETE_RESOLUTION}},
    )
    return True


def _clear_parent(server, user, token, issue_key):
    """Remove the parent link from an issue."""
    body = {"fields": {"parent": None}}
    api_call_with_retry(
        server, f"/issue/{issue_key}", user, token,
        body=body, method="PUT",
    )


def cleanup_strategy(server, user, token, strat_id, dry_run=False):
    """Clean up auto-created epics for a strategy.

    Returns (cleaned_count, error_count).
    """
    epics = _find_auto_epics(server, user, token, strat_id)
    if not epics:
        print(f"  No auto-created epics found")
        return 0, 0

    print(f"  Found {len(epics)} auto-created epic(s)")
    cleaned = 0
    errors = 0

    for epic in epics:
        key = epic["key"]
        summary = epic["fields"]["summary"]
        status = epic["fields"]["status"]["name"]

        if dry_run:
            print(f"  [DRY RUN] Would close and unlink: "
                  f"{key} ({status}) — {summary[:50]}")
            cleaned += 1
            continue

        try:
            if status.lower() != "closed":
                if _close_as_obsolete(server, user, token, key):
                    print(f"  Closed {key} as Obsolete")
                else:
                    print(f"  WARNING: Could not close {key} "
                          f"(status: {status})", file=sys.stderr)
            else:
                print(f"  {key} already closed")

            _clear_parent(server, user, token, key)
            print(f"  Unlinked {key} from {strat_id}")
            cleaned += 1
        except Exception as e:
            print(f"  ERROR on {key}: {e}", file=sys.stderr)
            errors += 1

    if not dry_run and cleaned > 0:
        try:
            remove_labels(server, user, token, strat_id, [STRAT_LABEL])
            print(f"  Removed {STRAT_LABEL} label from {strat_id}")
        except Exception as e:
            print(f"  ERROR removing label from {strat_id}: {e}",
                  file=sys.stderr)
            errors += 1
    elif dry_run:
        print(f"  [DRY RUN] Would remove {STRAT_LABEL} label "
              f"from {strat_id}")

    return cleaned, errors


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("strat_ids", nargs="+", metavar="RHAISTRAT-ID",
                        help="Strategy IDs to clean up")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned actions without making changes")
    args = parser.parse_args()

    for sid in args.strat_ids:
        if not re.match(r"^RHAISTRAT-\d+$", sid):
            parser.error(f"Invalid strategy ID: {sid}")

    server, user, token = require_env()
    if not args.dry_run and not all([server, user, token]):
        print("Error: JIRA_SERVER, JIRA_USER, and JIRA_TOKEN env vars "
              "required.", file=sys.stderr)
        sys.exit(1)

    total_cleaned = 0
    total_errors = 0

    for strat_id in args.strat_ids:
        print(f"\n{'='*60}")
        print(f"Cleanup: {strat_id}")
        print(f"{'='*60}")

        cleaned, errors = cleanup_strategy(
            server, user, token, strat_id, args.dry_run)
        total_cleaned += cleaned
        total_errors += errors

    print(f"\n{'='*60}")
    print(f"Summary: {total_cleaned} epics cleaned, "
          f"{total_errors} errors")
    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
