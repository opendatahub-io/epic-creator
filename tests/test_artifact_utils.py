#!/usr/bin/env python3
"""Tests for scripts/artifact_utils.py — schema validation, frontmatter I/O."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from artifact_utils import (
    SCHEMAS,
    ValidationError,
    apply_defaults,
    read_frontmatter,
    read_frontmatter_validated,
    update_frontmatter,
    validate,
    write_frontmatter,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(orig)


def _write(path, content):
    """Write a file, creating parent dirs."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


VALID_EPIC_FM = {
    "epic_id": "RHAISTRAT-1234-E001",
    "parent_strat": "RHAISTRAT-1234",
    "component": "dashboard",
    "team": "UI Team",
    "type": "Implementation",
    "priority": "P0",
}

VALID_REVIEW_FM = {
    "strat_id": "RHAISTRAT-1234",
    "score": 8,
    "pass": True,
    "recommendation": "accept",
}

VALID_SUMMARY_FM = {
    "parent_strat": "RHAISTRAT-1234",
    "epic_count": 5,
    "critical_path_length": 3,
}


# ── Schema & Validation ──────────────────────────────────────────────────────


class TestSchemas:
    def test_epic_task_schema_has_ai_signals(self):
        assert "ai_signals" in SCHEMAS["epic-task"]
        assert SCHEMAS["epic-task"]["ai_signals"]["type"] == "dict"

    def test_decomp_summary_has_revised(self):
        assert "revised" in SCHEMAS["decomp-summary"]
        spec = SCHEMAS["decomp-summary"]["revised"]
        assert spec["type"] == "bool"
        assert spec["default"] is False

    def test_decomp_review_has_issues(self):
        assert "issues" in SCHEMAS["decomp-review"]
        assert SCHEMAS["decomp-review"]["issues"]["type"] == "list"


class TestValidate:
    def test_valid_epic_data(self):
        errors = validate(VALID_EPIC_FM, "epic-task")
        assert errors == []

    def test_valid_review_data(self):
        errors = validate(VALID_REVIEW_FM, "decomp-review")
        assert errors == []

    def test_valid_summary_data(self):
        errors = validate(VALID_SUMMARY_FM, "decomp-summary")
        assert errors == []

    def test_unknown_field_rejected(self):
        data = {**VALID_EPIC_FM, "bogus": "value"}
        errors = validate(data, "epic-task")
        assert any("Unknown field: bogus" in e for e in errors)

    def test_missing_required_field(self):
        data = {**VALID_EPIC_FM}
        data.pop("epic_id")
        errors = validate(data, "epic-task")
        assert any("epic_id" in e for e in errors)

    def test_invalid_enum_value(self):
        data = {**VALID_EPIC_FM, "type": "banana"}
        errors = validate(data, "epic-task")
        assert any("banana" in e for e in errors)

    def test_invalid_priority(self):
        data = {**VALID_EPIC_FM, "priority": "P3"}
        errors = validate(data, "epic-task")
        assert any("P3" in e for e in errors)

    def test_wrong_type(self):
        data = {**VALID_REVIEW_FM, "score": "eight"}
        errors = validate(data, "decomp-review")
        assert any("expected int" in e for e in errors)

    def test_unknown_schema_type(self):
        with pytest.raises(ValueError, match="Unknown schema type"):
            validate({}, "nonexistent")

    def test_parent_strat_pattern(self):
        data = {**VALID_EPIC_FM, "parent_strat": "INVALID-123"}
        errors = validate(data, "epic-task")
        assert any("does not match" in e for e in errors)

    def test_ai_signals_nested_validation(self):
        data = {**VALID_EPIC_FM, "ai_signals": {"change_specificity": "bad"}}
        errors = validate(data, "epic-task")
        assert any("expected int" in e for e in errors)


class TestApplyDefaults:
    def test_revised_defaults_to_false(self):
        data = {**VALID_SUMMARY_FM}
        apply_defaults(data, "decomp-summary")
        assert data["revised"] is False

    def test_existing_value_not_overwritten(self):
        data = {**VALID_SUMMARY_FM, "revised": True}
        apply_defaults(data, "decomp-summary")
        assert data["revised"] is True

    def test_dependencies_defaults_to_empty_list(self):
        data = {**VALID_EPIC_FM}
        apply_defaults(data, "epic-task")
        assert data["dependencies"] == []

    def test_issues_defaults_to_empty_list(self):
        data = {**VALID_REVIEW_FM}
        apply_defaults(data, "decomp-review")
        assert data["issues"] == []


# ── read_frontmatter ──────────────────────────────────────────────────────────


class TestReadFrontmatter:
    def test_reads_yaml_and_body(self, tmp_dir):
        _write("test.md", "---\ntitle: Hello\n---\nBody here.\n")
        data, body = read_frontmatter("test.md")
        assert data["title"] == "Hello"
        assert "Body here." in body

    def test_no_frontmatter(self, tmp_dir):
        _write("test.md", "Just a plain file.\n")
        data, body = read_frontmatter("test.md")
        assert data == {}
        assert "Just a plain file." in body

    def test_missing_file(self, tmp_dir):
        data, body = read_frontmatter("nonexistent.md")
        assert data == {}
        assert body == ""


# ── write_frontmatter ─────────────────────────────────────────────────────────


class TestWriteFrontmatter:
    def test_creates_file(self, tmp_dir):
        write_frontmatter("out.md", VALID_REVIEW_FM.copy(), "decomp-review")
        assert os.path.exists("out.md")
        data, _ = read_frontmatter("out.md")
        assert data["strat_id"] == "RHAISTRAT-1234"

    def test_preserves_body(self, tmp_dir):
        _write("out.md", "---\nold: data\n---\nKeep this body.\n")
        write_frontmatter("out.md", VALID_REVIEW_FM.copy(), "decomp-review")
        data, body = read_frontmatter("out.md")
        assert data["strat_id"] == "RHAISTRAT-1234"
        assert "Keep this body." in body

    def test_preserves_body_without_frontmatter(self, tmp_dir):
        """Body-first pattern: agent writes body, then frontmatter.py set adds FM."""
        _write("out.md", "# Epic Title\n\nDescription here.\n")
        write_frontmatter("out.md", VALID_EPIC_FM.copy(), "epic-task")
        data, body = read_frontmatter("out.md")
        assert data["epic_id"] == "RHAISTRAT-1234-E001"
        assert "# Epic Title" in body
        assert "Description here." in body

    def test_rejects_invalid_data(self, tmp_dir):
        data = {**VALID_EPIC_FM, "type": "invalid"}
        with pytest.raises(ValidationError):
            write_frontmatter("out.md", data, "epic-task")

    def test_creates_parent_dirs(self, tmp_dir):
        write_frontmatter("a/b/c/out.md", VALID_REVIEW_FM.copy(), "decomp-review")
        assert os.path.exists("a/b/c/out.md")


# ── update_frontmatter ────────────────────────────────────────────────────────


class TestUpdateFrontmatter:
    def test_merges_updates(self, tmp_dir):
        write_frontmatter("summary.md", VALID_SUMMARY_FM.copy(), "decomp-summary")
        update_frontmatter("summary.md", {"revised": True}, "decomp-summary")
        data, _ = read_frontmatter("summary.md")
        assert data["revised"] is True
        assert data["parent_strat"] == "RHAISTRAT-1234"  # unchanged

    def test_merges_nested_dict(self, tmp_dir):
        data = {**VALID_EPIC_FM, "ai_signals": {
            "change_specificity": 1,
            "pattern_precedent": 0,
        }}
        write_frontmatter("epic.md", data, "epic-task")
        update_frontmatter("epic.md", {"ai_signals": {
            "pattern_precedent": 1,
            "adapter_pattern": -1,
        }}, "epic-task")
        result, _ = read_frontmatter("epic.md")
        assert result["ai_signals"]["change_specificity"] == 1  # preserved
        assert result["ai_signals"]["pattern_precedent"] == 1   # updated
        assert result["ai_signals"]["adapter_pattern"] == -1    # added

    def test_rejects_invalid_update(self, tmp_dir):
        write_frontmatter("summary.md", VALID_SUMMARY_FM.copy(), "decomp-summary")
        with pytest.raises(ValidationError):
            update_frontmatter("summary.md",
                               {"epic_count": "not_a_number"}, "decomp-summary")

    def test_issues_list_of_dicts(self, tmp_dir):
        """Review issues as list of dicts survives write/read cycle."""
        data = {**VALID_REVIEW_FM, "issues": [
            {"severity": "minor", "criterion": "DAG Coherence",
             "description": "test issue"},
        ]}
        write_frontmatter("review.md", data, "decomp-review")
        result, _ = read_frontmatter("review.md")
        assert len(result["issues"]) == 1
        assert result["issues"][0]["severity"] == "minor"
        assert result["issues"][0]["criterion"] == "DAG Coherence"
