<<<<<<< HEAD
# synodic-hooks
=======
# Synodic Hooks

Git safety and workflow automation hooks for Claude Code development.

**Philosophy**: Self-healing, non-blocking, and opinionated. Maximum productivity with minimum intervention.

## Features

### Claude Code Hooks

**Session Start** (`claude/session_start.py`)
- Auto-creates timestamped `claude/YYYYMMDDHHMMSS` branches
- Handles uncommitted changes from previous sessions (auto-commit with `⚠️ AUTOCOMMIT` prefix)
- Cleans up empty `claude/*` branches
- Provides session context

**Pre-Tool Use** (`claude/pre_tool_use.py`)
- Blocks git commits to non-`claude/*` branches
- Provides clear instructions when blocked
- Self-healing: errors don't block session

### Git Operation Scripts

**Pre-Commit** (`git/pre_commit.py`)
- Runs SwiftFormat and SwiftLint for Swift code
- Runs Ruff/Black for Python code
- Validates code quality before commit
- Callable from `.githooks/pre-commit`

**Pre-Push** (`git/pre_push.py`)
- Runs test suites before push
- Follows `scripts/pre_push` or `scripts/test` convention
- Auto-detects Swift/Python/Node projects
- Callable from `.githooks/pre-push`

## Quick Start

### 1. Clone Repository

```bash
# Clone to SynodicClaude directory
cd ~/Developer/SynodicClaude
git clone <repo-url> synodic-hooks

# Or create new repo
mkdir -p ~/Developer/SynodicClaude/synodic-hooks
cd ~/Developer/SynodicClaude/synodic-hooks
git init
# Copy files from this implementation
```

### 2. Symlink for Claude Code

```bash
# Symlink claude/ hooks to Claude Code hooks directory
ln -sf ~/Developer/SynodicClaude/synodic-hooks/claude ~/.claude/hooks

# Verify
ls -la ~/.claude/hooks/
# Should show symlink to synodic-hooks/claude/
```

### 3. Per-Repo Setup (Optional)

Add git hooks to specific repositories:

```bash
cd ~/Developer/your-project

# Copy hook templates
mkdir -p .githooks
cp ~/.claude/hooks-repo/templates/pre-commit .githooks/
cp ~/.claude/hooks-repo/templates/pre-push .githooks/
chmod +x .githooks/*

# Configure git to use .githooks directory
git config core.hooksPath .githooks

# Commit to version control
git add .githooks
git commit -m "Add git hooks for quality and testing"
```

### 4. Create Test Scripts (Recommended)

For automatic test execution on push:

```bash
# Create scripts directory
mkdir -p scripts

# Create test script
cat > scripts/pre_push << 'EOF'
#!/bin/bash
set -e

# Run your tests
swift test
# or: uv run pytest
# or: npm test

echo "✅ All tests passed"
EOF

chmod +x scripts/pre_push
```

## Usage

### Workflow

**Start Claude Code Session:**
1. Navigate to repo root: `cd ~/Developer/your-project`
2. Start Claude Code: `claude`
3. Hook automatically creates `claude/20250108143022` branch
4. Work on your changes

**Commit Changes:**
- Claude can commit to `claude/*` branches freely
- Attempts to commit to other branches are blocked with guidance

**Create Pull Request:**
```bash
# Push your claude/* branch
git push origin claude/20250108143022-feature-name

# Create PR via GitHub CLI or web UI
gh pr create --base develop --title "Feature: Add authentication"
```

**Merge via PR:**
- All merges to `develop`/`main` must go through Pull Requests
- Set up GitHub branch protection (see Configuration section)

### Branch Naming

**Auto-Created:**
```
claude/20250108143022          # First session
claude/20250108143022a         # Second session (same second)
```

**Rename for Clarity:**
```bash
# After understanding the task
git branch -m claude/20250108143022-add-authentication
```

**Pattern:**
```
claude/{timestamp}-{description}
claude/20250108143022-fix-login-bug
claude/20250108150000-refactor-auth
```

### Handling Uncommitted Changes

**Scenario:** You left uncommitted work in a previous session.

**What Happens:**
```
🚀 Session Started
📁 Project: your-project
📌 Branch: claude/20250107120000
⚠️  3 uncommitted file(s)
✅ Auto-committed 3 file(s) to claude/20250107120000
```

The hook auto-commits with message:
```
⚠️ AUTOCOMMIT 2025-01-08 14:30:22

Auto-committed 3 file(s) from previous session
```

**Quality Checks:**
- Git hooks (`pre-commit`) still run
- If quality checks fail, auto-commit is skipped
- You can fix and commit manually

### Empty Branch Cleanup

**What Gets Cleaned:**
- `claude/*` branches with zero unique commits
- Happens automatically on session start
- Current branch is never deleted

**Example:**
```
🗑️  Removed empty branch: claude/20250107100000
🗑️  Removed empty branch: claude/20250107110000
```

## Configuration

### GitHub Branch Protection

Protect `develop` and `main` branches to require PRs:

```bash
# Via GitHub CLI
gh api repos/OWNER/REPO/branches/develop/protection \
  --method PUT \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_pull_request_reviews[dismiss_stale_reviews]=true \
  --field enforce_admins=true

# Repeat for main branch
```

Or configure via GitHub web UI:
1. Settings → Branches → Add rule
2. Branch name pattern: `develop`
3. ✅ Require pull request before merging
4. ✅ Require approvals: 1
5. Save changes

### Bypassing Hooks

**When YOU need to commit to protected branches:**

```bash
# Bypass git hooks temporarily
git commit --no-verify -m "Emergency fix"

# Or set environment variable
SKIP_HOOKS=1 git commit -m "Direct commit"

# Bypass pre-push tests
git push --no-verify
```

**Note:** Claude Code hooks cannot be bypassed (by design).

### Customizing Quality Checks

Edit `git/pre_commit.py` to add project-specific checks:

```python
# Add custom validation
def run_custom_check(files: list[str], repo_path: Path) -> bool:
    """Your custom validation logic"""
    # Example: Check for TODOs in committed code
    for file in files:
        content = (repo_path / file).read_text()
        if "TODO" in content:
            emit_warning(f"Found TODO in {file}")
    return True  # Or False to block
```

## Architecture

```
synodic-hooks/
├── claude/                      # Claude Code hooks
│   ├── session_start.py         # Main entry point (78 lines)
│   ├── pre_tool_use.py          # Block commits to non-claude branches
│   └── session/                 # Session management modules
│       ├── __init__.py          # Public API
│       ├── branch_management.py # Branch creation & cleanup
│       ├── change_handler.py    # Uncommitted changes handling
│       └── reporter.py          # Session context reporting
├── git/                         # Git operation scripts
│   ├── pre_commit.py            # Format/lint validation
│   └── pre_push.py              # Test execution
├── shared/                      # Shared utilities
│   ├── hook_utils.py            # Hook data parsing & error formatting
│   └── git/                     # Git operations (modular)
│       ├── __init__.py          # Public API re-exports
│       ├── repo.py              # Repository detection
│       ├── status.py            # Branch & status queries
│       ├── branch.py            # Branch operations
│       └── claude.py            # Claude-specific git ops
├── templates/                   # Per-repo .githooks templates
│   ├── pre-commit               # Bash wrapper → git/pre_commit.py
│   └── pre-push                 # Bash wrapper → git/pre_push.py
└── tests/                       # All tests
    ├── test_git_utils.py
    └── test_pre_tool_use.py
```

**Design Philosophy:**
- **Small focused modules**: Largest file is 326 lines, average ~98 lines
- **Single responsibility**: Each module has one clear purpose
- **Package structure**: Related functionality grouped in `session/` and `git/` packages
- **Clean imports**: Import only what you need from focused modules

### Data Flow

**Session Start:**
```
Claude Code starts
→ session_start.py runs
  → Cleanup empty branches
  → Handle uncommitted changes (auto-commit if on claude/*)
  → Create new claude/* branch (if at repo root)
  → Report session context
→ Session continues
```

**Git Commit:**
```
Claude runs: git commit -m "message"
→ pre_tool_use.py intercepts
  → Check current branch
  → If not claude/*, BLOCK with guidance
  → If claude/*, ALLOW
→ If allowed, git commit proceeds
  → .githooks/pre-commit runs
    → git/pre_commit.py validates quality
    → If quality fails, commit blocked
    → If quality passes, commit succeeds
```

**Git Push:**
```
User runs: git push
→ .githooks/pre-push runs
  → git/pre_push.py runs tests
  → If tests fail, push blocked
  → If tests pass, push proceeds
→ GitHub branch protection enforces PR requirement
```

## Self-Healing Design

All hooks follow these principles:

**Never Block Session Start:**
- Errors in `session_start.py` emit warnings, session continues
- Missing git repos = skip, no error
- Failed auto-commit = warning, session continues

**Clear Error Messages:**
- All errors include fix suggestions
- LLM-friendly formatting for auto-repair
- File paths with line numbers when available

**Permissive on Tool Errors:**
- If SwiftFormat not found = warning, not failure
- If pytest not installed = skip tests, warn
- Unknown errors = allow operation, log error

**Examples:**

```python
# Good: Self-healing
try:
    run_swiftformat(files)
except FileNotFoundError:
    emit_warning("SwiftFormat not found - skipping")
    return True  # Don't block

# Bad: Brittle
run_swiftformat(files)  # Crashes if not installed
```

## Testing

```bash
cd ~/Developer/SynodicClaude/synodic-hooks

# Install pytest
uv add --dev pytest

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_git_utils.py -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html
```

## Troubleshooting

### Hook Not Running

**Check symlink:**
```bash
ls -la ~/.claude/hooks/
# Should point to synodic-hooks/claude/
```

**Recreate symlink:**
```bash
rm ~/.claude/hooks
ln -sf ~/Developer/SynodicClaude/synodic-hooks/claude ~/.claude/hooks
```

### Git Hooks Not Executing

**Check hooksPath:**
```bash
git config core.hooksPath
# Should output: .githooks
```

**Set hooksPath:**
```bash
git config core.hooksPath .githooks
```

**Check permissions:**
```bash
ls -la .githooks/
# Files should be executable (x flag)

chmod +x .githooks/*
```

### Auto-Commit Not Working

**Verify on claude/* branch:**
```bash
git branch --show-current
# Should start with "claude/"
```

**Check git status:**
```bash
git status
# Shows uncommitted files
```

**Manual commit:**
```bash
git add -A
git commit -m "Manual commit"
```

### Quality Checks Failing

**Run checks manually:**
```bash
# Swift
swiftformat-smart .
swiftlint-smart .

# Python
ruff format .
ruff check .
```

**Bypass temporarily:**
```bash
git commit --no-verify -m "Bypass quality checks"
```

## Migration Guide

### From Existing Hooks

If you have existing git hooks:

**Backup current hooks:**
```bash
cp -r .git/hooks .git/hooks.backup
```

**Migrate to .githooks:**
```bash
mkdir -p .githooks

# Copy custom logic to .githooks/
# Update to call synodic-hooks scripts

git config core.hooksPath .githooks
```

**Test:**
```bash
git commit -m "test"
# Verify hooks run
```

### From Manual Workflow

**Before:**
```bash
# Manual branch creation
git checkout -b feature/new-feature develop

# Manual quality checks
swiftformat .
swiftlint .

# Manual testing before push
swift test
git push
```

**After:**
```bash
# Automatic branch creation
claude  # Creates claude/20250108143022

# Automatic quality checks
git commit -m "changes"  # pre-commit hook runs

# Automatic testing
git push  # pre-push hook runs
```

## Contributing

### Adding New Hooks

1. Create hook script in `claude/` or `git/`
2. Follow self-healing patterns
3. Add tests in `tests/`
4. Update README documentation

### Code Style

- Use type hints
- Follow docstring format (Google style)
- Include self-healing error handling
- Emit clear user-facing messages

### Testing Changes

```bash
# Create test repo
mkdir /tmp/test-repo
cd /tmp/test-repo
git init
git config user.name "Test"
git config user.email "test@example.com"

# Symlink hooks
ln -sf ~/Developer/SynodicClaude/synodic-hooks/claude ~/.claude/hooks

# Test session start
claude  # or python3 ~/.claude/hooks/session_start.py
```

## FAQ

**Q: Why timestamped branch names?**
A: Automatic creation without conflicts. Rename for clarity once you understand the task.

**Q: Can I use this without Claude Code?**
A: Yes! The git hooks (`pre-commit`, `pre-push`) work independently.

**Q: What if I want to work on main directly?**
A: Bypass the Claude Code hook by running git commands directly (outside Claude session), or modify `pre_tool_use.py`.

**Q: Do I need hooks in every repo?**
A: No. Claude Code hooks work everywhere automatically. Per-repo git hooks (`.githooks/`) are optional for quality/testing.

**Q: How do I disable auto-branch creation?**
A: Start Claude Code from `~/Developer` (meta-directory) instead of repo root, or modify `session_start.py`.

**Q: Can I customize the timestamp format?**
A: Yes, edit `create_unique_claude_branch()` in `shared/git_utils.py`.

## License

[Your License Here]

## Support

Issues: [GitHub Issues URL]
Docs: [Documentation URL]
>>>>>>> claude/20251109-initial-consolidation
