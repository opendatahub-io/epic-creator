# Revise Decomposition Agent

You are revising an epic decomposition based on adversarial review feedback.

## Input

The variable `ID` contains the RHAISTRAT key (e.g., `RHAISTRAT-1234`).

Read the strategy from `artifacts/strat-tasks/<ID>.md`.
Read the review from `artifacts/epic-reviews/<ID>-decomp-review.md`.
Read the decomposition summary from `artifacts/epic-tasks/<ID>-decomposition.md`.
Read all epic files matching `artifacts/epic-tasks/<ID>-E*.md`.

## Steps

1. Parse the review's issues list
2. For each issue, determine the correction:
   - Missing HLR coverage → add epic or acceptance criteria
   - DAG error → fix dependency edges
   - Type misclassification → change epic type
   - Missing scope → add epic(s)
   - Scoring error → recalculate AI implementability
   - Missing ambiguity flag → add flag
3. Apply corrections to the epic files and decomposition summary
4. Update the decomposition summary frontmatter:
   - Set `revised: true`
   - Update `epic_count` and `critical_path_length` if they changed
   - Update `needs_clarification` if ambiguity flags changed

## Output

Updated epic files in `artifacts/epic-tasks/` and updated decomposition summary.
The decomposition summary frontmatter must have `revised: true` when complete.
