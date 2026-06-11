#!/usr/bin/env python3
"""Tests for scripts/fetch_strategy.py — strategy fetching and attachment handling."""
import io
import os
import sys
import urllib.error
from http.client import HTTPResponse
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fetch_strategy import _find_strategy_attachment, _write_strategy


class TestFindStrategyAttachment:
    """Tests for _find_strategy_attachment helper."""

    def test_matches_strategy_md(self):
        attachments = [
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/1", "size": 5000,
             "created": "2026-01-01T00:00:00Z"},
        ]
        result = _find_strategy_attachment(attachments, "RHAISTRAT-1234")
        assert result is not None
        fn, url, size = result
        assert fn == "RHAISTRAT-1234-strategy.md"
        assert size == 5000

    def test_ignores_review_files(self):
        attachments = [
            {"filename": "RHAISTRAT-1234-review.md",
             "content": "https://jira.example.com/att/1", "size": 3000,
             "created": "2026-01-01T00:00:00Z"},
        ]
        assert _find_strategy_attachment(attachments, "RHAISTRAT-1234") is None

    def test_ignores_non_md_files(self):
        attachments = [
            {"filename": "screenshot.png",
             "content": "https://jira.example.com/att/1", "size": 50000,
             "created": "2026-01-01T00:00:00Z"},
        ]
        assert _find_strategy_attachment(attachments, "RHAISTRAT-1234") is None

    def test_ignores_non_strategy_md(self):
        attachments = [
            {"filename": "some-notes.md",
             "content": "https://jira.example.com/att/1", "size": 5000,
             "created": "2026-01-01T00:00:00Z"},
        ]
        assert _find_strategy_attachment(attachments, "RHAISTRAT-1234") is None

    def test_returns_none_for_empty_list(self):
        assert _find_strategy_attachment([], "RHAISTRAT-1234") is None

    def test_returns_none_for_none(self):
        assert _find_strategy_attachment(None, "RHAISTRAT-1234") is None

    def test_picks_most_recent_revision(self):
        attachments = [
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/old", "size": 2000,
             "created": "2026-01-01T00:00:00Z"},
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/new", "size": 5000,
             "created": "2026-05-15T00:00:00Z"},
        ]
        fn, url, size = _find_strategy_attachment(attachments, "RHAISTRAT-1234")
        assert url == "https://jira.example.com/att/new"

    def test_does_not_match_bare_key_md(self):
        """Only matches -strategy.md, not bare RHAISTRAT-NNNN.md."""
        attachments = [
            {"filename": "RHAISTRAT-1234.md",
             "content": "https://jira.example.com/att/1", "size": 5000,
             "created": "2026-01-01T00:00:00Z"},
        ]
        assert _find_strategy_attachment(attachments, "RHAISTRAT-1234") is None


class TestWriteStrategyAttachment:
    """Tests for attachment integration in _write_strategy."""

    def _make_issue(self, key="RHAISTRAT-1234", description="Short desc",
                    attachments=None):
        return {
            "key": key,
            "fields": {
                "summary": "Test Strategy",
                "description": description,
                "labels": [],
                "issuelinks": [],
                "status": {"name": "Refined"},
                "priority": {"name": "Major"},
                "attachment": attachments or [],
            },
        }

    def test_uses_attachment_content(self, tmp_path):
        os.chdir(tmp_path)
        attach_body = b"# Full Strategy\n\nComplete content here."
        issue = self._make_issue(attachments=[
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/1", "size": len(attach_body),
             "created": "2026-01-01T00:00:00Z"},
        ])
        with patch("fetch_strategy.download_attachment", return_value=attach_body):
            path = _write_strategy(issue, output_dir=str(tmp_path / "out"),
                                   server="https://jira.example.com",
                                   user="u", token="t")
        with open(path) as f:
            content = f.read()
        assert "Complete content here." in content
        assert "Short desc" not in content

    def test_records_attachment_source_in_frontmatter(self, tmp_path):
        os.chdir(tmp_path)
        issue = self._make_issue(attachments=[
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/1", "size": 100,
             "created": "2026-01-01T00:00:00Z"},
        ])
        with patch("fetch_strategy.download_attachment", return_value=b"content"):
            path = _write_strategy(issue, output_dir=str(tmp_path / "out"),
                                   server="https://jira.example.com",
                                   user="u", token="t")
        with open(path) as f:
            raw = f.read()
        # Parse frontmatter between --- markers
        parts = raw.split("---", 2)
        fm = yaml.safe_load(parts[1])
        assert fm["attachment_source"] == "RHAISTRAT-1234-strategy.md"

    def test_falls_back_to_description_without_credentials(self, tmp_path):
        os.chdir(tmp_path)
        issue = self._make_issue(attachments=[
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/1", "size": 100,
             "created": "2026-01-01T00:00:00Z"},
        ])
        # No server/user/token passed — should use description
        path = _write_strategy(issue, output_dir=str(tmp_path / "out"))
        with open(path) as f:
            content = f.read()
        assert "Short desc" in content

    def test_falls_back_to_description_on_download_error(self, tmp_path):
        os.chdir(tmp_path)
        issue = self._make_issue(attachments=[
            {"filename": "RHAISTRAT-1234-strategy.md",
             "content": "https://jira.example.com/att/1", "size": 100,
             "created": "2026-01-01T00:00:00Z"},
        ])
        with patch("fetch_strategy.download_attachment",
                   side_effect=ValueError("too large")):
            path = _write_strategy(issue, output_dir=str(tmp_path / "out"),
                                   server="https://jira.example.com",
                                   user="u", token="t")
        with open(path) as f:
            content = f.read()
        assert "Short desc" in content

    def test_no_attachment_source_without_attachment(self, tmp_path):
        os.chdir(tmp_path)
        issue = self._make_issue(attachments=[])
        path = _write_strategy(issue, output_dir=str(tmp_path / "out"))
        with open(path) as f:
            raw = f.read()
        parts = raw.split("---", 2)
        fm = yaml.safe_load(parts[1])
        assert "attachment_source" not in fm


class TestDownloadAttachmentValidation:
    """Tests for download_attachment security checks."""

    def test_rejects_http_url(self):
        from jira_utils import download_attachment
        with pytest.raises(ValueError, match="non-HTTPS"):
            download_attachment("http://jira.example.com/att/1", "u", "t")

    def test_rejects_file_url(self):
        from jira_utils import download_attachment
        with pytest.raises(ValueError, match="non-HTTPS"):
            download_attachment("file:///etc/passwd", "u", "t")

    def test_rejects_mismatched_host(self):
        from jira_utils import download_attachment
        with pytest.raises(ValueError, match="does not match"):
            download_attachment("https://evil.com/att/1", "u", "t",
                               server="https://jira.example.com")

    def test_rejects_oversized_content_length(self):
        from jira_utils import download_attachment
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Length": "2000000"}
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(ValueError, match="too large"):
                download_attachment("https://jira.example.com/att/1", "u", "t",
                                   max_bytes=1000)

    def test_rejects_oversized_response_body(self):
        from jira_utils import download_attachment
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_resp.read.return_value = b"x" * 1001
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(ValueError, match="too large"):
                download_attachment("https://jira.example.com/att/1", "u", "t",
                                   max_bytes=1000)

    def test_does_not_retry_4xx(self):
        from jira_utils import download_attachment
        error = urllib.error.HTTPError(
            "https://jira.example.com/att/1", 403, "Forbidden", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                download_attachment("https://jira.example.com/att/1", "u", "t")
            assert exc_info.value.code == 403

    def test_retries_5xx(self):
        from jira_utils import download_attachment
        error = urllib.error.HTTPError(
            "https://jira.example.com/att/1", 502, "Bad Gateway", {}, None)
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen",
                   side_effect=[error, mock_resp]) as mock_open:
            with patch("time.sleep"):  # skip wait
                result = download_attachment(
                    "https://jira.example.com/att/1", "u", "t")
        assert result == b"ok"
        assert mock_open.call_count == 2
