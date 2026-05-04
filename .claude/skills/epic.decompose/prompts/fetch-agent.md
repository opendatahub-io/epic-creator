# Fetch Strategy Agent

You are fetching a single RHAISTRAT strategy from Jira and saving it as a local artifact.

## Input

The variable `ID` contains the RHAISTRAT key (e.g., `RHAISTRAT-1234`).

## Steps

1. Fetch the strategy from Jira using `python3 scripts/fetch_strategy.py fetch-one <ID>`
2. Verify the output file exists at `artifacts/strat-tasks/<ID>.md`
3. If the fetch fails, report the error and exit

## Output

A strategy file at `artifacts/strat-tasks/<ID>.md` with YAML frontmatter containing:
- strat_id, title, size, status, labels, teams, components

Do not modify the strategy content — write it exactly as fetched from Jira.
