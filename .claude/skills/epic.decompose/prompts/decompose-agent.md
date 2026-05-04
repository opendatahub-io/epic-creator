# Decompose Strategy Agent

You are decomposing a single RHAISTRAT strategy into an implementation epic DAG.

## Input

The variable `ID` contains the RHAISTRAT key (e.g., `RHAISTRAT-1234`).

Read the strategy from `artifacts/strat-tasks/<ID>.md`.
Read architecture context from `.context/architecture-context/`.
Read the decomposition algorithm from `docs/epic-decomposition-design.md`.

## Algorithm

Follow Steps 0-8 from the epic decomposition design document exactly:
- Step 0: Triage (below-threshold, docs-only)
- Step 1: Parse strategy scope
- Step 1.5: Parse Staff Engineer Input
- Step 2: Parse strategy scope (extract component graph, HLRs, dependencies, ACs, NFRs)
- Step 3: Build component graph
- Step 3.5: Identify Investigation epics
- Step 4: Map HLRs to epics
- Step 5: Build dependency DAG
- Step 5.5: Detect tiered delivery
- Step 6: Classify and score AI implementability
- Step 6.5: Strategy health warnings and ambiguity flags
- Step 7: Derive acceptance criteria
- Step 8: Generate epic artifacts

## Output

Write per-epic files to `artifacts/epic-tasks/`:
- `<ID>-E001.md`, `<ID>-E002.md`, etc. — one per epic with frontmatter
- `<ID>-decomposition.md` — summary with DAG, traceability matrix, ambiguity flags

Each epic file must have frontmatter with: epic_id, parent_strat, component, team, type, implementation_type, priority, dependencies, ai_implementability, ai_implementability_score.

The decomposition summary must have frontmatter with: parent_strat, needs_clarification, epic_count, critical_path_length.
