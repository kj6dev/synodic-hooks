# Claude Code Hooks - Design Principles

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
- Routes to appropriate formatter based on file extension
- Uses compiled Swift binaries for Swift files (fast, native)
- Uses Python + uv for Python files
- Future: Can add formatters for any language

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
8. **SessionStart** - Session initialization
9. **SessionEnd** - Session finalization (save state, reports)
