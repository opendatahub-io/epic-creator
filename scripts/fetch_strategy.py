#!/usr/bin/env python3
"""Fetch RHAISTRAT strategies from Jira REST API.

Usage:
    python3 scripts/fetch_strategy.py fetch "<JQL>" --ids-file <path> [--limit N]
    python3 scripts/fetch_strategy.py fetch-one <RHAISTRAT-ID>
"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from jira_utils import require_env, get_issue, api_call_with_retry, adf_to_markdown

import yaml


def _fetch_issue(server, user, token, key):
    fields = ["summary", "description", "labels", "issuelinks", "status",
              "priority"]
    return get_issue(server, user, token, key, fields=fields)


def _write_strategy(issue_data, output_dir="artifacts/strat-tasks"):
    key = issue_data["key"]
    fields = issue_data["fields"]
    title = fields.get("summary", "")
    desc_raw = fields.get("description")
    labels = fields.get("labels", [])
    status = fields.get("status", {}).get("name", "")
    priority = fields.get("priority", {}).get("name", "")

    if isinstance(desc_raw, dict):
        description = adf_to_markdown(desc_raw).strip()
    elif desc_raw:
        description = str(desc_raw).strip()
    else:
        description = ""

    links = []
    for link in fields.get("issuelinks", []):
        if "outwardIssue" in link:
            target = link["outwardIssue"]["key"]
            direction = link["type"].get("outward", "")
            links.append(f"{direction} {target}")
        elif "inwardIssue" in link:
            target = link["inwardIssue"]["key"]
            direction = link["type"].get("inward", "")
            links.append(f"{direction} {target}")

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{key}.md")

    frontmatter = {
        "strat_id": key,
        "title": title,
        "status": status,
        "priority": priority,
        "labels": labels if labels else [],
        "links": links if links else [],
    }

    with open(path, "w") as f:
        f.write("---\n")
        f.write(yaml.dump(frontmatter, default_flow_style=False,
                          sort_keys=False, allow_unicode=True))
        f.write("---\n\n")
        f.write(description)
        f.write("\n")

    return path


def _search_issues(server, user, token, jql, limit=100):
    """Search for issues using JQL with pagination via /search/jql."""
    all_issues = []
    fields = "summary,description,labels,issuelinks,status,priority"
    next_page_token = None

    while len(all_issues) < limit:
        batch_size = min(50, limit - len(all_issues))
        path = (f"/search/jql?jql={urllib.parse.quote(jql, safe='')}"
                f"&maxResults={batch_size}&fields={fields}")
        if next_page_token:
            path += f"&nextPageToken={urllib.parse.quote(next_page_token, safe='')}"
        data = api_call_with_retry(server, path, user, token)

        issues = data.get("issues", [])
        if not issues:
            break

        all_issues.extend(issues)

        if data.get("isLast", True):
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return all_issues


def cmd_fetch(args):
    import argparse
    parser = argparse.ArgumentParser(prog="fetch_strategy.py fetch")
    parser.add_argument("jql", help="JQL query string")
    parser.add_argument("--ids-file", required=True,
                        help="Output file for fetched IDs")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max issues to fetch")
    parser.add_argument("--data-dir", help="Data directory (unused, for compat)")
    opts = parser.parse_args(args)

    server, user, token = require_env()
    if not all([server, user, token]):
        print("ERROR: JIRA_SERVER, JIRA_USER, and JIRA_TOKEN must be set",
              file=sys.stderr)
        sys.exit(1)

    issues = _search_issues(server, user, token, opts.jql, opts.limit)

    all_keys = []
    for issue in issues:
        key = issue["key"]
        _write_strategy(issue)
        all_keys.append(key)
        print(f"Fetched {key}: {issue['fields'].get('summary', '')[:60]}",
              file=sys.stderr)

    os.makedirs(os.path.dirname(opts.ids_file) or "tmp", exist_ok=True)
    with open(opts.ids_file, "w") as f:
        for key in all_keys:
            f.write(f"{key}\n")

    print(f"Fetched {len(all_keys)} strategies", file=sys.stderr)


def cmd_fetch_one(args):
    if not args:
        print("Usage: fetch-one <RHAISTRAT-ID>", file=sys.stderr)
        sys.exit(1)
    key = args[0]
    server, user, token = require_env()
    if not all([server, user, token]):
        print("ERROR: JIRA_SERVER, JIRA_USER, and JIRA_TOKEN must be set",
              file=sys.stderr)
        sys.exit(1)
    issue = _fetch_issue(server, user, token, key)
    if not issue:
        sys.exit(1)
    path = _write_strategy(issue)
    print(path)


COMMANDS = {
    "fetch": cmd_fetch,
    "fetch-one": cmd_fetch_one,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Commands: {', '.join(COMMANDS)}", file=sys.stderr)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
