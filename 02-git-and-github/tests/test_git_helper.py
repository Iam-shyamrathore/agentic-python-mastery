"""Tests for Topic 02: Git Helper & Security Linter."""

import sys
from pathlib import Path
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from git_helper import (
    check_for_sensitive_files,
    get_git_branch,
    is_valid_conventional_commit,
)


def test_valid_conventional_commits():
    valid_examples = [
        "feat: add Gemini 2.0 streaming support",
        "fix(fastapi): handle null embedding response gracefully",
        "docs: update FREE_API_KEYS_GUIDE.md with Groq instructions",
        "refactor(db): convert synchronous session to async session",
        "test(agent): add test for tool execution loops",
        "chore: bump langchain version",
        "feat(rag)!: change default embedding dimension",
    ]
    for msg in valid_examples:
        assert is_valid_conventional_commit(msg) is True, f"Failed on: {msg}"


def test_invalid_conventional_commits():
    invalid_examples = [
        "fixed some stuff",
        "WIP",
        "Update README.md",
        "FEAT: all caps is invalid",
        "feat no colon",
    ]
    for msg in invalid_examples:
        assert is_valid_conventional_commit(msg) is False, f"Should fail on: {msg}"


def test_branch_detection():
    branch = get_git_branch(Path(__file__).parent.parent)
    assert isinstance(branch, str)
    assert len(branch) > 0
