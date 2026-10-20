# 🐙 Topic 02: Git & GitHub for AI Engineers

> **Master version control, conventional commit standards, automated API key leak prevention, and robust CI/CD quality gates for autonomous AI agents.**

---

## 🎯 Why Version Control & Git Security Matter in AI Engineering

In modern AI systems, autonomous coding agents (Claude Code, Cursor, Copilot, SWE-bench runners) generate, modify, and commit code continuously. A single vulnerability in your repository quality gate can:
1. **Leak High-Privilege API Keys**: OpenAI, Anthropic, Google Gemini, and Groq keys accidentally staged into a public GitHub repository are harvested by automated scrapers within **30 to 90 seconds**.
2. **Corrupt Agent PR Automation**: Semantic release pipelines, changelog generators, and branch policies rely on Conventional Commits (`feat:`, `fix:`, `refactor:`). Unstructured commit messages break continuous deployment.
3. **Trigger Detached HEAD Pipeline Failures**: Containerized CI runners and agent worktrees often operate in detached HEAD states. Without resilient branch detection, deployment scripts fail silently.

---

## 💥 Production War Stories & Hard-Learned Lessons

### 💥 War Story 1: The $14,000 Overnight Key Scraping Incident
> **The Scenario:** A developer testing an autonomous LangChain agent wrote a quick test script:
> ```python
> # ❌ test_eval.py
> OPENAI_API_KEY = "sk-proj-..."
> ```
> The developer ran `git add . && git commit -m "WIP" && git push origin main`.
> 
> **The Incident:** Even though the commit was force-reverted 8 minutes later, GitHub's public event API mirrors commits instantly across third-party archives. Within 90 seconds, an automated scraper in Eastern Europe extracted the key and launched thousands of concurrent `gpt-4` batch embeddings, racking up **$14,200 in API charges** by 4:00 AM before OpenAI's automated abuse detection severed the account.
> 
> **The Fix:** Never rely on file name checks alone. Implement pre-commit hooks and CI gates that scan file *contents* with high-precision regular expressions detecting `sk-proj-`, `sk-ant-`, `AIzaSy`, and `gsk_` tokens.

---

### 💥 War Story 2: The Agentic Merge Conflict Lockout
> **The Scenario:** A team ran 4 parallel subagents implementing different tools on feature branches. Each agent executed `git merge main` when finishing.
> 
> **The Incident:** Because two agents modified `tools/__init__.py` simultaneously, a 3-way merge conflict was generated with standard conflict markers (`<<<<<<< HEAD`, `=======`). When the next agent read the file to register another tool, the Python interpreter crashed with `SyntaxError: invalid syntax`. The agent attempted to "fix" the syntax error by deleting the conflicting tool registrations, wiping out another agent's work.
> 
> **The Fix:** Enforce a strict **Rebase & Linear History** workflow (`git fetch origin && git rebase origin/main`) with pre-merge validation checks in CI.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. Essential Daily Git Commands for AI Engineers

```bash
# Check status and diff
git status -s
git diff --staged

# Branching & Switching (Modern Git 2.23+ syntax)
git switch -c feature/rag-pipeline    # Create & switch branch
git switch main                      # Switch back to main

# Staging & Committing
git add .
git commit -m "feat(rag): add ChromaDB vector store retriever"

# Keeping branches updated (Rebase workflow)
git fetch origin
git rebase origin/main

# Undoing mistakes safely
git restore <file>                   # Discard working directory changes
git restore --staged <file>          # Unstage a file
git reset --soft HEAD~1              # Undo last commit, keep changes staged
```

---

### 2. Conventional Commits Standard

Professional AI repositories adhere to the Conventional Commits specification:

| Prefix | When to Use | Example |
| :--- | :--- | :--- |
| `feat:` | A new user-facing feature or model capability | `feat(agent): add tool calling for web search` |
| `fix:` | A bug fix | `fix(fastapi): handle null embedding response gracefully` |
| `docs:` | Documentation changes only | `docs(readme): add free Groq API key setup guide` |
| `refactor:` | Code change that neither fixes a bug nor adds a feature | `refactor(db): convert synchronous session to async session` |
| `test:` | Adding missing tests or correcting existing tests | `test(task): add edge case tests for task status transitions` |
| `chore:` | Maintenance, dependencies, tooling updates | `chore(deps): bump langchain to v0.2.5` |

#### Intelligent Commit Linter & Suggester
Our elevated `git_helper.py` provides automated suggestions:
- `"fixed stuff"` $\rightarrow$ `💡 Suggestion: "fix: resolve stuff"`
- `"add gemini streaming"` $\rightarrow$ `💡 Suggestion: "feat: add gemini streaming"`
- `"updated documentation"` $\rightarrow$ `💡 Suggestion: "feat: update documentation"`

---

### 3. High-Precision Regex Patterns for AI Secrets

| Provider | Key Format / Prefix | Regex Pattern |
| :--- | :--- | :--- |
| **OpenAI** | `sk-...` or `sk-proj-...` | `\b(sk-[a-zA-Z0-9]{20,}\|sk-proj-[a-zA-Z0-9_-]{20,})\b` |
| **Anthropic** | `sk-ant-...` | `\b(sk-ant-[a-zA-Z0-9_-]{20,})\b` |
| **Google Gemini** | `AIzaSy...` (39 chars total) | `\b(AIzaSy[a-zA-Z0-9_-]{33})\b` |
| **Groq** | `gsk_...` | `\b(gsk_[a-zA-Z0-9]{30,})\b` |
| **Private Keys** | `BEGIN ... PRIVATE KEY` | `-----BEGIN (?:RSA\|EC\|DSA\|OPENSSH) PRIVATE KEY-----` |

---

## 🛠️ The Hands-on Project: Git Security & Quality Gate

In this module, you will build `git_helper.py` to:
- Detect tracked and local sensitive files (`.env`, `id_rsa`, `*.pem`)
- Scan file contents using regex to catch leaked AI provider keys (OpenAI, Anthropic, Gemini, Groq)
- Lint commit messages against Conventional Commit rules with automated correction suggestions
- Accurately determine git branch state, including detached HEAD handling

### Running the Tests
```bash
pytest 02-git-and-github/tests/test_git_helper.py -v
```
