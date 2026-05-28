# Epic Creator

Skills for decomposing refined RHAISTRAT strategies into implementation epic DAGs.

## Artifact Conventions

All skills read from and write to the `artifacts/` directory in the working directory.

```
artifacts/
  strat-tasks/                # Fetched strategy files (input)
    RHAISTRAT-1234.md          # Strategy with YAML frontmatter

  epic-tasks/                 # Decomposition output (per-epic files)
    RHAISTRAT-1234-E001.md     # Per-epic files with frontmatter
    RHAISTRAT-1234-E002.md
    RHAISTRAT-1234-decomposition.md  # Summary: DAG, traceability, ambiguity flags

  epic-reviews/               # Adversarial review of decomposition
    RHAISTRAT-1234-decomp-review.md

  decompose-runs/             # Pipeline run reports
    2026-05-04T12-00-00Z.yaml
```

### Frontmatter

All task and review files use YAML frontmatter for structured metadata. Skills must use `scripts/frontmatter.py` to read schemas, set fields, and read validated data — never write YAML by hand.

```bash
# Get schema for a file type
python3 scripts/frontmatter.py schema strat-task
python3 scripts/frontmatter.py schema epic-task
python3 scripts/frontmatter.py schema decomp-review

# Set/update frontmatter on a file
python3 scripts/frontmatter.py set <path> field=value field=value ...

# Read validated frontmatter as JSON
python3 scripts/frontmatter.py read <path>
```

### State Persistence

Long-running skills use `scripts/state.py` to persist state to `tmp/` files so it survives context compression. All skills must use this utility instead of inline bash commands (cat, echo, mkdir) to avoid unnecessary auth prompts.

```bash
python3 scripts/state.py init <file> key=value ...    # Create config file
python3 scripts/state.py set <file> key=value ...     # Update keys in place
python3 scripts/state.py set-default <file> key=value ...  # Set only if key absent
python3 scripts/state.py read <file>                  # Print file contents
python3 scripts/state.py write-ids <file> ID ...      # Write ID list (one per line, deduped)
python3 scripts/state.py read-ids <file>              # Print IDs space-separated
python3 scripts/state.py timestamp                    # Print current UTC time (ISO 8601)
```

## Jira Integration

### Read Operations (fetch strategies)

Read operations use the Jira REST API via `scripts/fetch_strategy.py`.

### Write Operations (attach decomposition, apply labels)

Write operations use `scripts/attach_decomposition.py` to:
- Attach decomposition output as a file to the RHAISTRAT
- Apply `decomp-ready` label

Required environment variables:

```
JIRA_SERVER=https://your-site.atlassian.net
JIRA_USER=your-email@example.com
JIRA_TOKEN=your-api-token
```

## Jira Field Mappings

### RHAISTRAT Project
- **Project**: `RHAISTRAT`
- **Issue Type**: `Feature`
- **Labels applied by this pipeline**: `decomp-ready`

## Pipeline Execution Constraint

When `tmp/pipeline-state.yaml` exists and the phase is not DONE:

1. A text-only response (no tool call) during pipeline execution terminates the CI process.
2. After launching each wave of agents, your next Bash call MUST be
   `python3 scripts/pipeline_state.py wait-for-wave`. This is a blocking
   synchronization barrier that reads artifact files on disk. On exit 3,
   re-run the same command.
3. Do not wait for agent-completion notifications — the wait-for-wave command
   is unrelated to the Agent tool's notification system.

## Architecture Context

The pipeline fetches architecture context from [opendatahub-io/architecture-context](https://github.com/opendatahub-io/architecture-context) into `.context/architecture-context/` at bootstrap. A component is "in the platform" if it has an architecture context file.

Architecture context is used during decomposition to:
- Validate component existence and dependencies
- Determine upstream dependency maturity
- Inform AI implementability scoring (Signal 9: architecture claims)
