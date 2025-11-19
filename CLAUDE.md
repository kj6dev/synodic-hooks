# Claude Code Hooks - Design Principles

## Official Documentation

**Always refer to the official Claude Code hooks documentation:**
https://code.claude.com/docs/en/hooks

This is the authoritative source for:
- Hook types and their capabilities
- Hook input/output data structures
- Hook lifecycle and execution order
- Best practices and examples

## Error Handling Philosophy

### Rich Error Messages Over Logging

**Principle**: Provide rich, actionable error messages directly in the conversation rather than logging to files.

**Rationale**:
1. **Self-Healing**: The LLM can immediately identify and fix hook issues when they occur in context
2. **Simplicity**: No log rotation, no cleanup scripts, no file management overhead
3. **Visibility**: Errors appear exactly when and where they matter - in the active conversation
4. **Context**: The LLM has full conversation context to understand *why* the error happened
5. **Immediacy**: Problems are solved in real-time rather than discovered later

**Implementation**:
- All hooks wrap main logic in try/except
- Use `format_hook_error()` from hook_utils.py for consistent formatting
- Include: problem description, file location, actionable fix suggestion, stack trace
- Always exit 0 (permissive) to avoid blocking workflow
- Print to stderr for visibility

**Error Message Format**:
```
🚨 Hook Error: [HookName]
Problem: [Clear description]
File: [Full path:line_number]
Fix: [Actionable suggestion]

[Stack trace if available]
```

**Example Benefits**:
- ImportError → "Fix: Add 'import os' to hook_utils.py"
- KeyError → "Fix: Missing expected key in hook data: 'user_message'"
- FileNotFoundError → "Fix: Check path: /path/to/file"

**When to Use Logging Instead**:
- Only if hooks fail frequently in ways that are hard to debug
- If you need historical pattern analysis
- Start simple - add logging only if necessary

### Lint Violations as Errors

**Principle**: Report ALL lint violations as errors (not warnings) to ensure Claude's attention.

**Rationale**:
- Claude Code's attention mechanism prioritizes "errors" over "warnings"
- Violations formatted as warnings often get ignored or deprioritized
- Using `emit_error()` (🚨) ensures violations appear as critical issues requiring immediate attention

**Implementation Pattern** (see `formatters/swift.py`):
```python
# Capture tool output and exit code
result = subprocess.run([tool], capture_output=True, text=True)

if result.returncode == 0:
    emit_success(f"{tool_name} passed")
else:
    # Violations found - use emit_error() for header/footer only
    emit_error(f"LINT VIOLATIONS in {file_name} - {tool_name}")
    print("=" * 60)

    # Print violation details normally (readable for many violations)
    for line in result.stdout.strip().split("\n"):
        print(line)

    # Add helpful hints as errors (actionable guidance)
    hints = add_violation_hints(result.stdout)
    for hint in hints:
        emit_error(hint)

    print("=" * 60)
    emit_error(f"Fix these {tool_name} violations")
```

**Output Format**:
```
🚨 LINT VIOLATIONS in MyFile.swift - SwiftLint
============================================================
MyFile.swift:42:5: error: Line length exceeds 120 characters
MyFile.swift:89:1: error: Trailing whitespace
🚨 💡 Tip: Use `enum Constants` at the top of the type declaration
============================================================
🚨 Fix these SwiftLint violations
```

**Key Behaviors**:
- Hook remains permissive (exits 0) to allow workflow continuation
- Header/footer use `emit_error()` to trigger Claude's error attention mechanism
- Violation lines print normally for readability (not overwhelming with 50+ violations)
- Context-specific hints use `emit_error()` for visibility
- File:line:column format for easy navigation

## Hook Architecture

### Modular Design with Registry Pattern

**Formatters Directory**:
- Each language has its own formatter file (python.py, swift.py, typescript.py, json.py)
- Registry pattern in `__init__.py` for automatic discovery
- Easy to extend - just add a new formatter file and register extensions

**Shared Utilities**:
- `hook_utils.py` provides common functionality across all hooks
- Eliminates code duplication
- Functions: get_hook_data(), get_tool_name(), run_command(), format_hook_error()

**Hook Separation**:
- Each hook type (PreToolUse, PostToolUse, etc.) has its own Python file
- Clear separation of concerns
- Easy to understand and maintain

## File Organization

### Smart Config Discovery (Swift Tools)

The Swift quality tools (swiftformat-smart, swiftlint-smart, swiftlintcustom-smart) implement intelligent configuration discovery:

1. Check for `--config` parameter (explicit override)
2. Look for config in current directory (.swiftformat.yml, .swiftlint.yml)
3. Walk up directory tree until config found
4. Fall back to shared configs in ~/Developer/swift-quality-tools/Configs/
5. Error if no config found (fail fast)

This enables:
- Project-specific configs when needed
- Consistent shared defaults across all projects
- No manual config path management

### Integration Points

**Claude Code Hooks**:
- PostToolUse hook runs formatters after file edits
- PostToolUse hook suggests batch editing after 5 Swift file edits (performance optimization)
- PreToolUse hook **blocks** bare `swiftlint`/`swiftformat` commands (enforces `-smart` usage)
- Routes to appropriate formatter based on file extension
- Uses compiled Swift binaries for Swift files (fast, native)
- Uses Python + uv for Python files
- Future: Can add formatters for any language

**Batch Editing Performance Hint**:
- After 3 Swift file edits in a session, PostToolUse suggests batching
- Shown once per session to avoid spam
- Helps Claude optimize workflow when fixing many violations
- Batching reduces hook overhead: 10 edits = 1 hook run vs 10 hook runs

**Xcode Build Phases**:
- Swift quality tools can be called from Xcode build scripts
- Provides in-IDE warnings and errors
- Consistent quality checks across all development environments

## Development Workflow

### Hook Development Guidelines

1. **Always import format_hook_error** from hook_utils
2. **Wrap main() in try/except** for all hooks
3. **Provide context** in error messages ("Processing file X", "Validating tool Y")
4. **Exit 0 on errors** to avoid blocking workflow (permissive mode)
5. **Test error paths** - errors should be helpful, not cryptic

### Adding New Formatters

1. Create new file in `formatters/` directory (e.g., `rust.py`)
2. Import `register_formatter` from `__init__.py`
3. Implement `format_[language](file_path: Path, project_dir: Path) -> bool`
4. Register extensions at module level: `register_formatter([".rs"], format_rust)`
5. The registry automatically discovers and loads it

### Testing Hooks

- Run hooks directly: `python3 ~/.claude/hooks/[hook_name].py`
- Hooks gracefully handle missing stdin (return empty dict)
- Use test scripts to verify error formatting
- All hooks should be permissive (exit 0) unless explicitly blocking

## System Paths

- **Hooks**: `~/.claude/hooks/` → `~/Developer/synodic-hooks/claude/`
- **Swift Tools**: `~/Developer/swift-quality-tools/.build/release/`
- **Formatters**: `~/Developer/synodic-hooks/claude/formatters/`
- **Shared Configs**: `~/Developer/swift-quality-tools/Configs/`

## Hook Types Available

1. **PreToolUse** - Validate/block operations before execution
2. **PostToolUse** - Format/lint files after edits
3. **UserPromptSubmit** - Process prompts before Claude sees them
4. **Notification** - Handle Claude notifications (sound, logging)
5. **Stop** - Session completion (sound, cleanup)
6. **SubagentStop** - Subagent task completion
7. **PreCompact** - Before context compaction (archive, save)
8. **SessionStart** - Session initialization (see below for details)
9. **SessionEnd** - Session finalization (save state, reports)

### SessionStart Hook Responsibilities

The SessionStart hook runs when a Claude Code session starts or resumes:

1. **Sync CLAUDE.md Template** - Auto-updates `.claude/sessions/CLAUDE.md` in each repository to ensure consistent documentation about committing session files
2. **Sync .gitattributes Rule** - Auto-adds linguist-generated rule to collapse session files in GitHub PRs
3. **Check Uncommitted Session Files** - Warns about uncommitted `.claude/sessions/*.yml` files from previous work to prevent losing context
4. **Clean Up Empty Branches** - Removes empty or merged `claude/*` branches from previous sessions
5. **Report Session Context** - Shows current branch, uncommitted changes, and existing claude/* branches

**Template Sync**:
- Template file: `~/Developer/synodic-hooks/templates/sessions-CLAUDE.md`
- Target location: `<repo-root>/.claude/sessions/CLAUDE.md`
- Only updates if template has changed (hash-based comparison)
- Creates directory structure if needed

**GitAttributes Sync**:
- Auto-adds `.claude/sessions/*.yml linguist-generated=true` to `.gitattributes`
- Preserves existing .gitattributes content
- Idempotent - only adds if rule doesn't exist
- Creates .gitattributes if it doesn't exist

**Uncommitted Files Warning**:
```
⚠️ ============================================================
⚠️ 📋 Uncommitted session files from previous work:
   .claude/sessions/20251116-105715.yml
   .claude/sessions/20251116-171730.yml
⚠️
⚠️ 💡 Consider committing these to preserve development context
⚠️    See .claude/sessions/CLAUDE.md for details
⚠️ ============================================================
```

This warning appears at session start (not end) because:
- Early notification when action can be taken
- Reminds about work from previous sessions
- Non-blocking - session continues regardless

## Session File Logging

### Purpose
Captures ALL file edits (not just Swift) with user intent for future pattern analysis and skill development.

### Implementation
- **UserPromptSubmit**: Captures prompts to session-specific cache (`~/.claude-prompt-{session_id}.json`)
- **PreToolUse**: Logs all text file edits to **per-repo** session files in `.claude/sessions/`

### Per-Repo Session Files

**Location**: `<repo-root>/.claude/sessions/YYYYMMDD-HHMMSS.yml`

**Key Behavior**:
- Logs are saved to the repo WHERE THE FILE IS EDITED, not where Claude Code is running
- Example: Editing synodic-cc-config files while running from synodic-hooks → logs go to synodic-cc-config/.claude/sessions/
- Each session gets a unique YAML file with metadata header
- Session files are reused if < 4 hours old

**Session Metadata**:
```yaml
---
# Session Metadata
session_id: claude-20251116-105715
started: 2025-11-16T10:57:15.123456
repo: /Users/bryancostanza/Developer/synodic-hooks
branch: claude/feature-name
edit_count: 0
---
```

### What Gets Logged
**All text file edits via Edit tool** (with filtering):
- Timestamp
- File path
- Change type (refactor, bugfix, feature, docs, style, test)
- User prompt (intent behind the edit)
- Old code
- New code

**Filtered out** (to prevent noise/loops):
- **.claude/sessions/** files themselves (prevents infinite loop on commit)
- **.claude/current_session** file
- Binary files
- Large files (> 1MB)
- Massive edits (> 10,000 lines)
- Lock files (package-lock.json, yarn.lock, etc.)
- Build outputs (/build/, /dist/, /.build/, /node_modules/)

### Prompt Capture Strategy
1. **Primary**: Session-specific cache (fast, clean)
   - Written by UserPromptSubmit hook
   - `~/.claude-prompt-{session_id}.json`
   - No multi-session conflicts
2. **Fallback**: Transcript parsing (reliable)
   - Reads conversation history
   - Finds last user message

### Output Format
YAML with readable multi-line strings:
```yaml
---
# Edit 2025-11-16T10:58:23.456789
time: 2025-11-16T10:58:23.456789
file: /path/to/ContentView.swift
change_type: refactor
user_prompt: |
  Extract the body into a computed property
old: |
  var body: some View {
      VStack { ... }
  }
new: |
  var body: some View {
      content
  }

  private var content: some View { ... }
```

### Session Files and Git

**CRITICAL**: Session files should be committed with code changes.

**Policy**:
- ✅ **DO commit** `.claude/sessions/` files with your changes
- ✅ Session files provide valuable context for code changes
- ✅ Multiple projects can commit their own session files independently
- ❌ **DO NOT** add `.claude/` to `.gitignore`

**Why commit session files?**
- Documents the intent behind code changes (user prompts)
- Provides pattern analysis data for skill development
- Creates audit trail of AI-assisted development
- Enables future preference discovery and rule extraction

**Reducing PR Noise**:
Session files can balloon PR sizes. The SessionStart hook automatically adds this rule to `.gitattributes`:

```gitattributes
# Collapse session files in GitHub PR diffs
.claude/sessions/*.yml linguist-generated=true
```

This keeps session files committed (preserving context) while reducing visual noise during code review. The rule is auto-synced to all repositories on session start.

**Infinite Loop Prevention**:
Session files themselves are excluded from logging to prevent:
1. Commit code + session file
2. Hook logs commit → updates session file
3. Session file dirty again → cycle repeats

The exclude filter breaks this loop by not logging edits to `.claude/sessions/` or `.claude/current_session`.

### Use Cases
- Pattern detection for skill updates (Swift, Python, TypeScript, etc.)
- Training data collection across all languages
- Refactoring pattern analysis
- Code quality metrics over time
- Change type analysis (refactor vs bugfix vs feature)
