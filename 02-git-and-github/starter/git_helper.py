"""Topic 02: Git Helper & Security Linter (Starter Template).

Complete each TODO section alongside your AI Assistant.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_-]+\))?!?: .+$"
)

SENSITIVE_PATTERNS = [
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
]


def is_valid_conventional_commit(message: str) -> bool:
    """Validate whether a commit message adheres to Conventional Commits."""
    # TODO: Strip whitespace and check against CONVENTIONAL_COMMIT_REGEX
    raise NotImplementedError("Implement is_valid_conventional_commit")


def check_for_sensitive_files(repo_path: Path | str) -> list[str]:
    """Scan staged or tracked files for sensitive names like .env or keys."""
    # TODO: Use git ls-files or directory walk to detect sensitive files
    raise NotImplementedError("Implement check_for_sensitive_files")


def get_git_branch(repo_path: Path | str) -> str:
    """Return the name of the current git branch."""
    # TODO: Run 'git branch --show-current' and return branch name
    raise NotImplementedError("Implement get_git_branch")


def main() -> None:
    print("Welcome to Git Helper & Quality Gate! Use this with your AI Agent mentor.")


if __name__ == "__main__":
    main()
