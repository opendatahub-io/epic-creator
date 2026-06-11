#!/usr/bin/env python3
"""Tests for scripts/frontmatter.py CLI — set command, JSON list parsing, body preservation."""
import json
import os
import subprocess

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "frontmatter.py")


def run_fm(*args):
    """Run frontmatter.py and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["python3", SCRIPT, *args],
        capture_output=True, text=True,
    )
    return result.stdout, result.stderr, result.returncode


def _write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


@pytest.fixture
def tmp_dir(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(orig)


class TestSetCreateFile:
    """frontmatter.py set creates files that don't exist."""

    def test_creates_epic_task(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        out, err, rc = run_fm(
            "set", "artifacts/epic-tasks/RHAISTRAT-1234-E001.md",
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=RHAISTRAT-1234",
            "component=dashboard",
            "team=UI Team",
            "type=Implementation",
            "priority=P0",
        )
        assert rc == 0
        assert "OK:" in out

        # Verify file has frontmatter
        read_out, _, read_rc = run_fm(
            "read", "artifacts/epic-tasks/RHAISTRAT-1234-E001.md")
        assert read_rc == 0
        data = json.loads(read_out)
        assert data["epic_id"] == "RHAISTRAT-1234-E001"
        assert data["type"] == "Implementation"

    def test_creates_decomp_summary(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        out, _, rc = run_fm(
            "set", "artifacts/epic-tasks/RHAISTRAT-1234-decomposition.md",
            "parent_strat=RHAISTRAT-1234",
            "epic_count=5",
            "critical_path_length=3",
        )
        assert rc == 0

        read_out, _, _ = run_fm(
            "read", "artifacts/epic-tasks/RHAISTRAT-1234-decomposition.md")
        data = json.loads(read_out)
        assert data["epic_count"] == 5
        assert data["revised"] is False  # default

    def test_creates_decomp_review(self, tmp_dir):
        os.makedirs("artifacts/epic-reviews", exist_ok=True)
        out, _, rc = run_fm(
            "set", "artifacts/epic-reviews/RHAISTRAT-1234-decomp-review.md",
            "strat_id=RHAISTRAT-1234",
            "score=7",
            "pass=true",
            "recommendation=accept",
        )
        assert rc == 0

        read_out, _, _ = run_fm(
            "read", "artifacts/epic-reviews/RHAISTRAT-1234-decomp-review.md")
        data = json.loads(read_out)
        assert data["pass"] is True
        assert data["issues"] == []  # default


class TestSetPreservesBody:
    """Body-first pattern: write body, then frontmatter.py set adds FM."""

    def test_body_preserved_on_epic_task(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-E001.md"
        _write(path, "# My Epic\n\nDescription of the epic.\n\n## Scope\n- Item 1\n")

        run_fm(
            "set", path,
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=RHAISTRAT-1234",
            "component=dashboard",
            "team=UI Team",
            "type=Implementation",
            "priority=P0",
        )

        with open(path) as f:
            content = f.read()

        assert "---\n" in content  # has frontmatter
        assert "# My Epic" in content
        assert "Description of the epic." in content
        assert "- Item 1" in content

    def test_body_preserved_on_summary(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-decomposition.md"
        _write(path, "## Epic List\n\n| ID | Title |\n|---|---|\n")

        run_fm(
            "set", path,
            "parent_strat=RHAISTRAT-1234",
            "epic_count=3",
            "critical_path_length=2",
        )

        with open(path) as f:
            content = f.read()

        assert "## Epic List" in content
        assert "| ID | Title |" in content


class TestSetDotNotation:
    """Dot notation for nested dict fields (ai_signals, gate_failure_impact)."""

    def test_ai_signals_dot_notation(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-E001.md"
        out, _, rc = run_fm(
            "set", path,
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=RHAISTRAT-1234",
            "component=dashboard",
            "team=UI Team",
            "type=Implementation",
            "priority=P0",
            "ai_signals.change_specificity=1",
            "ai_signals.pattern_precedent=-1",
            "ai_signals.open_questions=0",
        )
        assert rc == 0

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert data["ai_signals"]["change_specificity"] == 1
        assert data["ai_signals"]["pattern_precedent"] == -1
        assert data["ai_signals"]["open_questions"] == 0

    def test_gate_failure_impact_dot_notation(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-E001.md"
        run_fm(
            "set", path,
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=RHAISTRAT-1234",
            "component=dashboard",
            "team=UI Team",
            "type=Implementation",
            "priority=P0",
            "gate_failure_impact.action=rewrite",
            "gate_failure_impact.fallback_approach=Use fallback API",
        )

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert data["gate_failure_impact"]["action"] == "rewrite"
        assert data["gate_failure_impact"]["fallback_approach"] == "Use fallback API"


class TestSetCommaSeparatedList:
    """Comma-separated values for list fields (dependencies)."""

    def test_dependencies_comma_separated(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-E003.md"
        run_fm(
            "set", path,
            "epic_id=RHAISTRAT-1234-E003",
            "parent_strat=RHAISTRAT-1234",
            "component=api",
            "team=Backend Team",
            "type=Implementation",
            "priority=P1",
            "dependencies=RHAISTRAT-1234-E001,RHAISTRAT-1234-E002",
        )

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert data["dependencies"] == [
            "RHAISTRAT-1234-E001",
            "RHAISTRAT-1234-E002",
        ]

    def test_empty_list(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-E001.md"
        run_fm(
            "set", path,
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=RHAISTRAT-1234",
            "component=api",
            "team=Backend Team",
            "type=Implementation",
            "priority=P0",
            "dependencies=[]",
        )

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        # [] coerces to None via the "null/none/[]" branch
        assert data["dependencies"] == []  # default applied


class TestSetJsonList:
    """JSON array values for list fields (issues in decomp-review)."""

    def test_issues_json_array(self, tmp_dir):
        os.makedirs("artifacts/epic-reviews", exist_ok=True)
        path = "artifacts/epic-reviews/RHAISTRAT-1234-decomp-review.md"
        issues_json = json.dumps([
            {"severity": "minor", "criterion": "DAG Coherence",
             "description": "Test issue one"},
            {"severity": "major", "criterion": "HLR Coverage",
             "description": "Missing P1 HLR mapping"},
        ])
        run_fm(
            "set", path,
            "strat_id=RHAISTRAT-1234",
            "score=6",
            "pass=true",
            "recommendation=accept",
            f"issues={issues_json}",
        )

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert len(data["issues"]) == 2
        assert data["issues"][0]["severity"] == "minor"
        assert data["issues"][1]["criterion"] == "HLR Coverage"

    def test_issues_empty_json_array(self, tmp_dir):
        os.makedirs("artifacts/epic-reviews", exist_ok=True)
        path = "artifacts/epic-reviews/RHAISTRAT-1234-decomp-review.md"
        run_fm(
            "set", path,
            "strat_id=RHAISTRAT-1234",
            "score=14",
            "pass=true",
            "recommendation=accept",
            "issues=[]",
        )

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert data["issues"] == []


class TestSetValidation:
    """frontmatter.py set rejects invalid data."""

    def test_invalid_type_rejected(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        _, err, rc = run_fm(
            "set", "artifacts/epic-tasks/RHAISTRAT-1234-E001.md",
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=RHAISTRAT-1234",
            "component=dashboard",
            "team=UI Team",
            "type=BadType",
            "priority=P0",
        )
        assert rc != 0
        assert "Error" in err

    def test_unknown_field_rejected(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        _, err, rc = run_fm(
            "set", "artifacts/epic-tasks/RHAISTRAT-1234-E001.md",
            "bogus_field=value",
        )
        assert rc != 0
        assert "unknown field" in err.lower() or "Error" in err

    def test_invalid_parent_strat_pattern(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        _, err, rc = run_fm(
            "set", "artifacts/epic-tasks/RHAISTRAT-1234-E001.md",
            "epic_id=RHAISTRAT-1234-E001",
            "parent_strat=INVALID-123",
            "component=dashboard",
            "team=UI Team",
            "type=Implementation",
            "priority=P0",
        )
        assert rc != 0


class TestSetUpdate:
    """frontmatter.py set updates existing files."""

    def test_update_revised_flag(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-decomposition.md"
        _write(path, "## Epic List\n\nBody content.\n")

        # Create initial frontmatter
        run_fm("set", path,
               "parent_strat=RHAISTRAT-1234",
               "epic_count=5",
               "critical_path_length=3")

        # Update revised flag
        run_fm("set", path, "revised=true")

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert data["revised"] is True
        assert data["epic_count"] == 5  # preserved

    def test_update_revised_false(self, tmp_dir):
        os.makedirs("artifacts/epic-tasks", exist_ok=True)
        path = "artifacts/epic-tasks/RHAISTRAT-1234-decomposition.md"

        run_fm("set", path,
               "parent_strat=RHAISTRAT-1234",
               "epic_count=5",
               "critical_path_length=3")

        run_fm("set", path, "revised=false")

        read_out, _, _ = run_fm("read", path)
        data = json.loads(read_out)
        assert data["revised"] is False
