"""Topic 02: Git Helper & Security Linter (Complete Reference Solution).

Provides automated commit message linting with intelligent suggestions,
deep sensitive file and API key secret scanning using regex patterns,
and robust git branch detection for AI development workflows.

Why this matters in AI Engineering:
-----------------------------------
1. Catastrophic API Key Leaks:
   AI applications consume high-privilege keys (OpenAI, Anthropic, Google Gemini, Groq).
   GitHub mirrors public commits across global cache servers within seconds. Once a secret
   is pushed, automated botnets scrape and exploit it in under 60 seconds, incurring
   thousands of dollars in unauthorized inference bills.

2. Automated Agent CI/CD Quality Gates:
   When autonomous coding agents create Pull Requests or commit code, they must adhere to
   strict repository standards. Automated linters reject non-conventional commit messages
   and block pushes containing credential patterns before they ever reach a remote repository.

3. Robust Branch Hygiene:
   Agents operating in CI/CD or dockerized containers often run in detached HEAD states
   or ephemeral worktrees. Branch detection must gracefully handle detached HEADs, initial
   commits, and non-git environments without crashing the pipeline.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import logging
from pathlib import Path
import re
import subprocess
import sys

# Configure structured standard logging
logger = logging.getLogger("git_helper")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_-]+\))?!?: .+$"
)

SENSITIVE_FILENAME_PATTERNS = [
    ".env",
    ".env.*",
    "*.env",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "credentials.json",
    "service_account.json",
]

# High-precision regular expressions for sensitive AI API keys and private certificates
SENSITIVE_CONTENT_PATTERNS: dict[str, re.Pattern[str]] = {
    "OpenAI API Key": re.compile(r"\b(sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_-]{20,})\b"),
    "Anthropic API Key": re.compile(r"\b(sk-ant-[a-zA-Z0-9_-]{20,})\b"),
    "Google Gemini API Key": re.compile(r"\b(AIzaSy[a-zA-Z0-9_-]{33})\b"),
    "Groq API Key": re.compile(r"\b(gsk_[a-zA-Z0-9]{30,})\b"),
    "Private Key Header": re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
}

IGNORE_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".tox",
    ".mypy_cache",
    "dist",
    "build",
}


@dataclass
class SecretMatch:
    """Represents a discovered secret in a file."""
    file_path: str
    line_number: int
    secret_type: str
    snippet: str

    def __str__(self) -> str:
        return f"{self.file_path}:{self.line_number} [{self.secret_type}] -> {self.snippet}"


def is_valid_conventional_commit(message: str) -> bool:
    """Validate whether a commit message adheres to the Conventional Commits specification.

    Args:
        message: The candidate commit message string.

    Returns:
        True if valid according to Conventional Commits specification, False otherwise.
    """
    clean = message.strip()
    if not clean:
        return False
    first_line = clean.split("\n")[0]
    return bool(CONVENTIONAL_COMMIT_REGEX.match(first_line))


def suggest_commit_message(message: str) -> str:
    """Generate a valid Conventional Commit suggestion for a poorly formatted message.

    Heuristics:
    - If already valid, returns unchanged.
    - Inspects leading verbs (fixed, added, updated, refactored, etc.) to infer the type.
    - Formats output as '<type>: <imperative description>'.

    Example:
        'fixed stuff' -> 'fix: resolve stuff'
        'Add gemini streaming' -> 'feat: add gemini streaming'
    """
    clean = message.strip()
    if is_valid_conventional_commit(clean):
        return clean

    # Strip trailing punctuation
    clean_line = clean.split("\n")[0].rstrip(".").strip()
    words = clean_line.split()
    if not words:
        return "chore: update repository"

    first_word = words[0].lower()
    rest = " ".join(words[1:]) if len(words) > 1 else ""

    # Common verb mappings
    if first_word in ("fixed", "fixes", "fixing"):
        desc = f"resolve {rest}" if rest else "resolve issue"
        return f"fix: {desc}"
    if first_word in ("fix", "repair", "bugfix"):
        desc = rest if rest else "resolve issue"
        return f"fix: {desc}"
    if first_word in ("added", "adds", "adding", "add", "implement", "implemented", "new"):
        desc = f"add {rest}" if first_word != "add" and rest else (rest if rest else "new feature")
        return f"feat: {desc}"
    if first_word in ("updated", "updates", "updating", "update"):
        desc = f"update {rest}" if rest else "update functionality"
        return f"feat: {desc}"
    if first_word in ("docs", "doc", "documentation", "readme"):
        desc = rest if rest else "update documentation"
        return f"docs: {desc}"
    if first_word in ("refactored", "refactoring", "refactor", "cleanup", "clean"):
        desc = rest if rest else "refactor codebase structure"
        return f"refactor: {desc}"
    if first_word in ("test", "tests", "testing", "tested"):
        desc = rest if rest else "add automated tests"
        return f"test: {desc}"
    if first_word in ("chore", "bump", "bumped", "bumping", "deps", "dependency", "dependencies"):
        desc = f"bump {rest}" if rest else "update project dependencies"
        return f"chore: {desc}"

    # Default fallback: lowercase first letter and prefix with feat or chore
    lowered = clean_line[0].lower() + clean_line[1:] if len(clean_line) > 1 else clean_line.lower()
    return f"feat: {lowered}"


def lint_commit_message(message: str) -> tuple[bool, str | None]:
    """Lint a commit message and provide a correction suggestion if invalid.

    Returns:
        Tuple of (is_valid: bool, suggestion: str | None).
    """
    if is_valid_conventional_commit(message):
        return True, None
    return False, suggest_commit_message(message)


def scan_file_for_secrets(file_path: Path, root_path: Path) -> list[SecretMatch]:
    """Scan an individual file for sensitive API keys and certificates.

    Args:
        file_path: Absolute path to the file to scan.
        root_path: Root repository directory for relative path calculation.

    Returns:
        List of `SecretMatch` instances representing detected secrets.
    """
    findings: list[SecretMatch] = []
    rel_path = str(file_path.relative_to(root_path))

    # Check filename patterns first
    for pattern in SENSITIVE_FILENAME_PATTERNS:
        if fnmatch.fnmatch(file_path.name, pattern):
            findings.append(
                SecretMatch(
                    file_path=rel_path,
                    line_number=1,
                    secret_type="Sensitive File Name",
                    snippet=f"File matches pattern '{pattern}'",
                )
            )
            break

    # Read content line by line to scan for regex patterns
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_idx, line in enumerate(f, start=1):
                # Skip excessively long lines (e.g. minified JS, compiled bundles)
                if len(line) > 2000:
                    continue
                for secret_type, regex in SENSITIVE_CONTENT_PATTERNS.items():
                    match = regex.search(line)
                    if match:
                        raw_key = match.group(0)
                        # Redact key for safe display: sk-proj-... -> sk-proj-***
                        redacted = raw_key[:7] + "..." + raw_key[-4:] if len(raw_key) > 12 else "***"
                        findings.append(
                            SecretMatch(
                                file_path=rel_path,
                                line_number=line_idx,
                                secret_type=secret_type,
                                snippet=redacted,
                            )
                        )
    except (OSError, UnicodeDecodeError) as exc:
        logger.debug("Skipping unreadable file %s: %s", rel_path, exc)

    return findings


def check_for_sensitive_files(repo_path: Path | str) -> list[str]:
    """Scan tracked, staged, and working directory files for sensitive names and API keys.

    Inspects both:
    1. File names against `SENSITIVE_FILENAME_PATTERNS` (.env, *.pem, id_rsa, etc.).
    2. File contents against `SENSITIVE_CONTENT_PATTERNS` (OpenAI, Anthropic, Gemini, Groq keys).

    Args:
        repo_path: Directory path of the repository to audit.

    Returns:
        Sorted list of unique relative file paths flagged as sensitive.
    """
    root = Path(repo_path).resolve()
    flagged_files: set[str] = set()

    # Determine files to inspect via git ls-files if available
    inspected_paths: set[Path] = set()
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        for rel in result.stdout.splitlines():
            clean_rel = rel.strip()
            if clean_rel:
                candidate = root / clean_rel
                if candidate.is_file():
                    inspected_paths.add(candidate)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # If git ls-files yielded nothing or failed, walk directory safely
    if not inspected_paths:
        for path in root.rglob("*"):
            if path.is_file() and not any(part in IGNORE_DIRECTORIES for part in path.parts):
                inspected_paths.add(path)

    # Scan all target files
    for path in inspected_paths:
        # Check filename pattern
        for pattern in SENSITIVE_FILENAME_PATTERNS:
            if fnmatch.fnmatch(path.name, pattern):
                try:
                    flagged_files.add(str(path.relative_to(root)))
                except ValueError:
                    flagged_files.add(path.name)
                break

        # Check file content
        findings = scan_file_for_secrets(path, root)
        if findings:
            for match in findings:
                flagged_files.add(match.file_path)

    return sorted(list(flagged_files))


def get_git_branch(repo_path: Path | str) -> str:
    """Return the name of the current git branch with robust fallback handling.

    Handles:
    - Active standard branch names (e.g. 'main', 'feature/rag').
    - Detached HEAD states (captures commit short SHA).
    - Freshly initialized repositories before initial commit.
    - Non-git directories or missing git binary.

    Args:
        repo_path: Path to the target git repository.

    Returns:
        Branch name string, 'HEAD (detached at <sha>)', or 'unknown'.
    """
    root = Path(repo_path).resolve()
    try:
        # 1. Primary check: git branch --show-current
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        if branch:
            return branch

        # 2. Check for detached HEAD or initial repo state
        rev_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_result.returncode == 0 and rev_result.stdout.strip():
            return f"HEAD (detached at {rev_result.stdout.strip()})"

        # 3. Check for unborn branch (e.g., git init with no commits yet)
        sym_result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if sym_result.returncode == 0 and sym_result.stdout.strip():
            return sym_result.stdout.strip()

        return "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> None:
    """CLI entrypoint for Git helper and security quality gate."""
    parser = argparse.ArgumentParser(description="Git Security & Conventional Commit Validator for AI Engineers")
    subparsers = parser.add_subparsers(dest="command")

    # Lint commit message
    lint_parser = subparsers.add_parser("lint-commit", help="Validate and lint a commit message")
    lint_parser.add_argument("message", help="Commit message to check")

    # Audit secrets
    audit_parser = subparsers.add_parser("audit-secrets", help="Deep scan repository for sensitive files and API keys")
    audit_parser.add_argument("--path", default=".", help="Repository root path")

    # Show branch
    branch_parser = subparsers.add_parser("branch", help="Get current git branch name")
    branch_parser.add_argument("--path", default=".", help="Repository root path")

    args = parser.parse_args()

    if args.command == "lint-commit":
        valid, suggestion = lint_commit_message(args.message)
        if valid:
            print(f"✅ Valid conventional commit: '{args.message}'")
        else:
            print(f"❌ Invalid commit format: '{args.message}'", file=sys.stderr)
            if suggestion:
                print(f"💡 Suggestion: '{suggestion}'", file=sys.stderr)
            print("Must match: feat|fix|docs|refactor|test|chore[(scope)]: description", file=sys.stderr)
            sys.exit(1)

    elif args.command == "audit-secrets":
        root = Path(args.path).resolve()
        sensitive = check_for_sensitive_files(root)
        if sensitive:
            print(f"🚨 WARNING: {len(sensitive)} sensitive file(s) or secret(s) detected:")
            for item in sensitive:
                print(f"  - {item}")
            sys.exit(1)
        else:
            print("🛡️ Clean! No sensitive files or leaked API keys detected.")

    elif args.command == "branch":
        branch = get_git_branch(args.path)
        print(f"🌿 Current branch: {branch}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
