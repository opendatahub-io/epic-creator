"""Shared artifact utilities — frontmatter reading."""

import os
import re


def read_frontmatter(path):
    """Read YAML frontmatter from a markdown file.

    Returns (dict, body_str). Returns ({}, "") if no frontmatter found.
    """
    import yaml

    if not os.path.exists(path):
        return {}, ""
    with open(path) as f:
        content = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not m:
        return {}, content
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, content
    return data, m.group(2)
