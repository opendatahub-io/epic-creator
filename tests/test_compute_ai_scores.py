#!/usr/bin/env python3
"""Tests for scripts/compute_ai_scores.py — Implementation sum + Investigation routing."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from artifact_utils import read_frontmatter, write_frontmatter
from compute_ai_scores import classify, classify_investigation, compute_for_epic


@pytest.fixture
def tmp_dir(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(orig)


def _inv(spec=0, src=0, run=0, cluster=0, human=0):
    return {"question_specificity": spec, "source_accessibility": src,
            "local_runnability": run, "cluster_hardware_dependence": cluster,
            "human_judgment_required": human}


# ── Implementation thresholds (unchanged behavior) ──────────────────────────

class TestImplementationClassify:
    @pytest.mark.parametrize("score,expected", [
        (3, "High"), (5, "High"), (2, "Medium"), (0, "Medium"),
        (-1, "Low"), (-3, "Low"),
    ])
    def test_thresholds(self, score, expected):
        assert classify(score) == expected


# ── Investigation routing model ─────────────────────────────────────────────

class TestInvestigationClassify:
    def test_calibration_against_run_investigations(self):
        # Profiles of four investigations from a real decomposition run, keyed
        # by shape rather than ticket id.
        cases = {
            "sdk-env-var-compliance": (_inv(spec=1, src=1, run=1), "High"),   # was Low under the 9-signal rubric
            "mlflow-otlp-ingestion":  (_inv(spec=1, src=1, run=1), "High"),
            "ui-view-existence":      (_inv(spec=1, src=1, run=0, human=-1), "Medium"),
            "architecture-decision":  (_inv(spec=1, src=0, run=0, human=-2), "Low"),
        }
        for name, (sig, expected) in cases.items():
            _, cls = classify_investigation(sig)
            assert cls == expected, f"{name}: got {cls}, expected {expected}"

    def test_high_requires_no_blockers(self):
        # Strong positives but a cluster blocker caps at Medium, not High.
        _, cls = classify_investigation(_inv(spec=1, src=1, run=1, cluster=-1))
        assert cls == "Medium"

    def test_pure_desk_is_high(self):
        # Readable but not runnable, no blockers -> still High (read OR run).
        _, cls = classify_investigation(_inv(spec=1, src=1, run=0))
        assert cls == "High"

    def test_no_oracle_guard_forces_low(self):
        # Neither readable-with-answer nor runnable -> Low regardless of spec.
        _, cls = classify_investigation(_inv(spec=1, src=0, run=0))
        assert cls == "Low"

    def test_vague_questions_force_low(self):
        _, cls = classify_investigation(_inv(spec=-1, src=1, run=1))
        assert cls == "Low"

    def test_net_negative_is_low(self):
        # Blockers outweigh the positives (total <= -1) -> Low.
        _, cls = classify_investigation(_inv(spec=1, src=1, run=1, cluster=-2, human=-2))
        assert cls == "Low"

    def test_oracle_plus_gating_blocker_is_hybrid(self):
        # A readable oracle exists (the AI can resolve part) but a gating human
        # decision remains -> hybrid/Medium, not Low. Contrast the architecture-
        # decision case, which has NO oracle (src=0) and so routes to a person.
        _, cls = classify_investigation(_inv(spec=1, src=1, run=0, human=-2))
        assert cls == "Medium"


# ── compute_for_epic dispatches on signal set ───────────────────────────────

class TestComputeForEpic:
    def _epic(self, fm):
        write_frontmatter("epic.md", {
            "epic_id": "RHAISTRAT-1-E001", "title": "t",
            "parent_strat": "RHAISTRAT-1", "component": "c", "team": "t",
            "priority": "P0", **fm}, "epic-task")
        compute_for_epic("epic.md")
        data, _ = read_frontmatter("epic.md")
        return data["ai_implementability"], data["ai_implementability_score"]

    def test_investigation_epic_uses_routing_model(self, tmp_dir):
        cls, score = self._epic({"type": "Investigation",
                                  "investigation_signals": _inv(spec=1, src=1, run=1)})
        assert cls == "High" and score == 3

    def test_implementation_epic_uses_signal_sum(self, tmp_dir):
        cls, score = self._epic({"type": "Implementation", "ai_signals": {
            "change_specificity": 1, "pattern_precedent": 1, "adapter_pattern": 0,
            "existing_foundation": 1, "open_questions": -1, "external_dependency": 0,
            "human_process_gates": -1, "repo_access": 1, "architecture_claims": 1}})
        assert cls == "High" and score == 3

    def test_dispatch_is_by_type_not_signal_presence(self, tmp_dir):
        # An Implementation epic carrying a stale investigation_signals block
        # must still be scored by the 9-signal sum, not the routing model.
        cls, score = self._epic({
            "type": "Implementation",
            "ai_signals": {"change_specificity": 1},          # sum = 1 -> Medium
            "investigation_signals": _inv(spec=1, src=1, run=1),  # +3 if mis-dispatched
        })
        assert cls == "Medium" and score == 1
