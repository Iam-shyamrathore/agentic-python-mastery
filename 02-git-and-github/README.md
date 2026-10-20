# 🐙 Topic 02: Git & GitHub for AI Engineers

> **Master essential version control, branching strategies, secret leak prevention, and automated CI/CD workflows for AI projects.**

---

## 🎯 Why Version Control Matters in AI Engineering

In AI development, repositories hold prompt templates, eval sets, model configs, agent pipelines, and deployment scripts. A single careless `git push` can:
1. Leak \$10,000+ worth of OpenAI or Anthropic API keys to public scrapers within seconds.
2. Commit multi-gigabyte model weights or vector database files, blowing up repository size.
3. Break agent orchestration pipelines in production due to unpinned dependencies.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. Essential Daily Git Commands

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
| `feat:` | A new user-facing feature or capability | `feat(agent): add tool calling for web search` |
| `fix:` | A bug fix | `fix(fastapi): handle null embedding response gracefully` |
| `docs:` | Documentation changes only | `docs(readme): add free Groq API key setup guide` |
| `refactor:` | Code change that neither fixes a bug nor adds a feature | `refactor(db): convert synchronous session to async session` |
| `test:` | Adding missing tests or correcting existing tests | `test(task): add edge case tests for task status transitions` |
| `chore:` | Maintenance, dependencies, tooling updates | `chore(deps): bump langchain to v0.2.5` |

---

### 3. Secret Leak Prevention Checklist

Before every push:
1. Ensure `.env` is explicitly inside `.gitignore`.
2. Run `git status` to ensure no keys or `.db` files are green (staged).
3. If an API key is ever accidentally committed, revoke it **immediately** in the provider dashboard—rewriting git history alone is not sufficient because GitHub mirrors commits rapidly.

---

## 🛠️ The Hands-on Project: Version-Controlled Project Workflow

In this module, you will build `git_helper.py` to:
- Programmatically verify Git repository cleanliness
- Detect accidentally tracked sensitive files (`.env`, `*.pem`, `*.key`)
- Validate commit message formats against Conventional Commit rules
- Generate GitHub Actions CI configuration for Python

### Running the Tests
```bash
pytest 02-git-and-github/tests/test_git_helper.py -v
```
