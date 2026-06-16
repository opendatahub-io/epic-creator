#!/usr/bin/env python3
"""Fetch RHAI project components from Jira and write to disk.

Writes the canonical component list to .context/rhai-components.txt
(one component name per line, sorted). This file is read by the
decomposer prompt to constrain component selection, and by submit.py
to validate before creating issues.

Usage:
    python scripts/fetch_components.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from jira_utils import require_env, api_call_with_retry

PROJECT = "RHAI"
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".context", "rhai-components.txt")


def fetch_components(server, user, token):
    """Fetch all component names from the RHAI project.

    Validates that names are non-empty and contain no newlines
    (which would corrupt the one-per-line file format).
    """
    components = api_call_with_retry(
        server, f"/project/{PROJECT}/components", user, token)
    names = []
    for c in components:
        name = c.get("name", "").strip()
        if not name or "\n" in name:
            print(f"  WARNING: Skipping invalid component name: {name!r}",
                  file=sys.stderr)
            continue
        names.append(name)
    return sorted(names)


def main():
    server, user, token = require_env()
    if not all([server, user, token]):
        print("Error: JIRA_SERVER, JIRA_USER, and JIRA_TOKEN env vars "
              "required.", file=sys.stderr)
        sys.exit(1)

    try:
        names = fetch_components(server, user, token)
    except Exception as e:
        print(f"Error fetching components: {e}", file=sys.stderr)
        sys.exit(1)

    if not names:
        print("Error: No components fetched from RHAI project.",
              file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        for name in names:
            f.write(f"{name}\n")

    print(f"Wrote {len(names)} components to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
