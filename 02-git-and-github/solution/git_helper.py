"""Topic 02: Git Helper & Security Linter (Complete Reference Solution).

Provides automated commit message linting, sensitive file detection,
and branch information utilities for AI development workflows.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path


CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_-]+\))?!?: .+$"
)

SENSITIVE_PATTERNS = [
    ".env",
    ".env.local",
    "*.env",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
]


def is_valid_conventional_commit(message: str) -> bool:
    """Validate whether a commit message adheres to Conventional Commits."""
    clean = message.strip()
    first_line = clean.split("\n")[0] if "\n" in clean else clean
    return bool(CONVENTIONAL_COMMIT_REGEX.match(first_line))


def check_for_sensitive_files(repo_path: Path | str) -> list[str]:
    """Scan tracked and staged files for sensitive files like .env or private keys."""
    root = Path(repo_path).resolve()
    flagged: list[str] = []

    try:
        # Run git ls-files to inspect tracked and staged files
        result = subprocess.run(
            ["git", "ls-files", "--stage"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 2:
                filename = parts[1]
                basename = Path(filename).name
                for pattern in SENSITIVE_PATTERNS:
                    if fnmatch.fnmatch(basename, pattern):
                        flagged.append(filename)
                        break
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to local file walk if not a git repo or git missing
        for path in root.rglob("*"):
            if path.is_file() and not any(p in path.parts for p in [".git", ".venv", "venv", "__pycache__"]):
                for pattern in SENSITIVE_PATTERNS:
                    if fnmatch.fnmatch(path.name, pattern):
                        flagged.append(str(path.relative_to(root)))
                        break

    return sorted(list(set(flagged)))


def get_git_branch(repo_path: Path | str) -> str:
    """Return the name of the current git branch."""
    root = Path(repo_path).resolve()
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch if branch else "HEAD (detached)"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Git Security & Conventional Commit Validator")
    subparsers = parser.add_subparsers(dest="command")

    # Lint commit message
    lint_parser = subparsers.add_parser("lint-commit", help="Validate a commit message")
    lint_parser.add_argument("message", help="Commit message to check")

    # Audit secrets
    audit_parser = subparsers.add_parser("audit-secrets", help="Check for sensitive files")
    audit_parser.add_argument("--path", default=".", help="Repository root path")

    args = parser.parse_args()

    if args.command == "lint-commit":
        valid = is_valid_conventional_commit(args.message)
        if valid:
            print(f"✅ Valid conventional commit: '{args.message}'")
        else:
            print(f"❌ Invalid commit format: '{args.message}'\nMust match: feat|fix|docs|refactor|test|chore[(scope)]: description", file=sys.stderr)
            sys.exit(1)

    elif args.command == "audit-secrets":
        sensitive = check_for_sensitive_files(args.path)
        if sensitive:
            print(f"🚨 WARNING: {len(sensitive)} sensitive file(s) detected:")
            for item in sensitive:
                print(f"  - {item}")
            sys.exit(1)
        else:
            print("🛡️ Clean! No tracked sensitive files detected.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
