#!/usr/bin/env python3
"""Fetch RHAISTRAT strategies from Jira REST API.

Usage:
    python3 scripts/fetch_strategy.py fetch "<JQL>" --ids-file <path> [--limit N]
    python3 scripts/fetch_strategy.py fetch-one <RHAISTRAT-ID>
"""

import json
import os
import re
import sys

import requests


def _jira_auth():
    server = os.environ.get("JIRA_SERVER")
    user = os.environ.get("JIRA_USER")
    token = os.environ.get("JIRA_TOKEN")
    if not all([server, user, token]):
        print("ERROR: JIRA_SERVER, JIRA_USER, and JIRA_TOKEN must be set",
              file=sys.stderr)
        sys.exit(1)
    return server, user, token


def _fetch_issue(server, user, token, key):
    url = f"{server}/rest/api/2/issue/{key}"
    params = {"fields": "summary,description,labels,issuelinks,status,priority"}
    resp = requests.get(url, auth=(user, token), params=params)
    if resp.status_code != 200:
        print(f"ERROR: Failed to fetch {key}: {resp.status_code}",
              file=sys.stderr)
        return None
    return resp.json()


def _write_strategy(issue_data, output_dir="artifacts/strat-tasks"):
    key = issue_data["key"]
    fields = issue_data["fields"]
    title = fields.get("summary", "")
    description = fields.get("description", "") or ""
    labels = fields.get("labels", [])
    status = fields.get("status", {}).get("name", "")
    priority = fields.get("priority", {}).get("name", "")

    links = []
    for link in fields.get("issuelinks", []):
        link_type = link.get("type", {}).get("name", "")
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

    with open(path, "w") as f:
        f.write("---\n")
        f.write(f"strat_id: {key}\n")
        f.write(f"title: \"{title}\"\n")
        f.write(f"status: {status}\n")
        f.write(f"priority: {priority}\n")
        f.write(f"labels:\n")
        for label in labels:
            f.write(f"  - {label}\n")
        if not labels:
            f.write(f"  []\n")
        f.write(f"links:\n")
        for link in links:
            f.write(f"  - \"{link}\"\n")
        if not links:
            f.write(f"  []\n")
        f.write("---\n\n")
        f.write(description)
        f.write("\n")

    return path


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

    server, user, token = _jira_auth()

    url = f"{server}/rest/api/2/search"
    start = 0
    all_keys = []

    while start < opts.limit:
        batch_size = min(50, opts.limit - start)
        params = {
            "jql": opts.jql,
            "startAt": start,
            "maxResults": batch_size,
            "fields": "summary,description,labels,issuelinks,status,priority",
        }
        resp = requests.get(url, auth=(user, token), params=params)
        if resp.status_code != 200:
            print(f"ERROR: JQL search failed: {resp.status_code}",
                  file=sys.stderr)
            sys.exit(1)

        data = resp.json()
        issues = data.get("issues", [])
        if not issues:
            break

        for issue in issues:
            key = issue["key"]
            _write_strategy(issue)
            all_keys.append(key)
            print(f"Fetched {key}: {issue['fields'].get('summary', '')[:60]}",
                  file=sys.stderr)

        start += len(issues)
        if start >= data.get("total", 0):
            break

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
    server, user, token = _jira_auth()
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
