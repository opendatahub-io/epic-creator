# Epic Creator

Claude Code plugin for decomposing RHAISTRAT strategies into implementation epic DAGs.

The `epic.decompose` skill takes a set of RHAISTRAT Jira tickets (by ID or JQL query), fetches each strategy, decomposes it into implementation epics with dependency graphs, runs adversarial review, and optionally revises the output. It operates as a non-interactive pipeline suitable for both manual and CI use.

## Installation

```bash
claude plugin marketplace add https://github.com/jwforres/epic-creator
claude plugin install epic-creator@jwforres
```

## Prerequisites

- Python 3.10+
- PyYAML (`pip install pyyaml`)
- Jira credentials as environment variables:
  ```
  JIRA_SERVER=https://your-site.atlassian.net
  JIRA_USER=your-email@example.com
  JIRA_TOKEN=your-api-token
  ```

## Usage

Invoke the skill in Claude Code:

```
/epic-creator:epic.decompose RHAISTRAT-1234 RHAISTRAT-5678
/epic-creator:epic.decompose --jql "project = RHAISTRAT AND labels = ready"
```

### Options

| Flag | Description |
|------|-------------|
| `--jql "<query>"` | Fetch strategies matching a JQL query |
| `--limit N` | Limit number of strategies to process |
| `--batch-size N` | Strategies per batch (default: 25) |
| `--headless` | Suppress interactive output |
| `--announce-complete` | Announce when pipeline finishes |
| `--reprocess` | Reprocess previously completed strategies |
| `--data-dir "<path>"` | Custom data directory |

## Artifacts

All output is written to `artifacts/` in the working directory:

```
artifacts/
  strat-tasks/              # Fetched strategy files
  epic-tasks/               # Decomposed epics with frontmatter
  epic-reviews/             # Adversarial review output
  decompose-runs/           # Pipeline run reports
```
