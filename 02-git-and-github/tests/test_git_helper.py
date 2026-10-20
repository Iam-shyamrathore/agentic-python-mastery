"""Tests for Topic 02: Git Helper & Security Linter."""

from pathlib import Path
import sys
import tempfile
import pytest

# Add solution directory to path for clean import
sys.path.insert(0, str(Path(__file__).parent.parent / "solution"))

from git_helper import (
    check_for_sensitive_files,
    get_git_branch,
    is_valid_conventional_commit,
    lint_commit_message,
    scan_file_for_secrets,
    suggest_commit_message,
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


def test_commit_linting_and_suggestions():
    """Verify intelligent suggestions for non-conventional commit messages."""
    test_cases = [
        ("fixed stuff", "fix: resolve stuff"),
        ("fixed memory leak in agent", "fix: resolve memory leak in agent"),
        ("add Gemini streaming", "feat: add Gemini streaming"),
        ("updated documentation for tools", "feat: update documentation for tools"),
        ("refactored database query builder", "refactor: database query builder"),
        ("testing tool retry loop", "test: tool retry loop"),
        ("bumped langchain dependency", "chore: update project dependencies"),
    ]
    for raw, expected_prefix in test_cases:
        is_valid, suggestion = lint_commit_message(raw)
        assert is_valid is False
        assert suggestion is not None
        assert is_valid_conventional_commit(suggestion), f"Suggestion '{suggestion}' must be valid!"
        assert suggestion.startswith(expected_prefix.split()[0]), f"Expected prefix for '{raw}', got '{suggestion}'"

    # Message already valid
    valid_msg = "feat: implement vector search"
    valid, suggestion = lint_commit_message(valid_msg)
    assert valid is True
    assert suggestion is None


def test_detect_sensitive_filenames():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".env").write_text("PORT=8000\n", encoding="utf-8")
        (root / "id_rsa").write_text("fake-key\n", encoding="utf-8")
        (root / "safe_file.py").write_text("print('hello')\n", encoding="utf-8")

        flagged = check_for_sensitive_files(root)
        assert ".env" in flagged
        assert "id_rsa" in flagged
        assert "safe_file.py" not in flagged


def test_detect_sensitive_api_keys_in_content():
    """Verify that regex scanning finds OpenAI, Anthropic, Google, and Groq keys inside files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # File with OpenAI key
        openai_file = root / "agent_config.py"
        openai_file.write_text("OPENAI_KEY = 'sk-proj-abc12345678901234567890xyz'\n", encoding="utf-8")

        # File with Anthropic key
        anthropic_file = root / "claude_client.py"
        anthropic_file.write_text("ANTHROPIC_API_KEY = 'sk-ant-api03-abcdef12345678901234567890'\n", encoding="utf-8")

        # File with Google Gemini key
        google_file = root / "gemini_service.py"
        google_file.write_text("GEMINI_KEY = 'AIzaSyD-1234567890123456789012345678901'\n", encoding="utf-8")

        # File with Groq key
        groq_file = root / "groq_runner.py"
        groq_file.write_text("GROQ_KEY = 'gsk_1234567890abcdef1234567890abcdef12345678'\n", encoding="utf-8")

        # Safe file
        safe_file = root / "normal.py"
        safe_file.write_text("USER_NAME = 'alice'\nVALUE = 42\n", encoding="utf-8")

        flagged = check_for_sensitive_files(root)
        assert "agent_config.py" in flagged
        assert "claude_client.py" in flagged
        assert "gemini_service.py" in flagged
        assert "groq_runner.py" in flagged
        assert "normal.py" not in flagged


def test_branch_detection():
    branch = get_git_branch(Path(__file__).parent.parent)
    assert isinstance(branch, str)
    assert len(branch) > 0


def test_branch_detection_non_git():
    with tempfile.TemporaryDirectory() as tmpdir:
        branch = get_git_branch(tmpdir)
        assert branch in ("unknown", "HEAD (detached)")
