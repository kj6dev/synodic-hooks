# Feature: Stale Binary Detection for Swift Packages

**Status**: Proposed
**Priority**: Medium
**Created**: 2025-11-13

## Problem

When Swift package source files are modified but binaries are not rebuilt, the compiled tools become stale. This causes:

1. **Help text inconsistencies**: `swiftlintcustom-smart --help` shows 12-line body limit, but source code uses 15
2. **Behavioral mismatches**: Tool behavior doesn't match latest code changes
3. **Silent failures**: No indication that binaries are outdated
4. **Quality issues**: Hook violations use old rules instead of updated ones

**Real Example:**
- Modified `test-custom-rule.swift:45` to use 15-line limit
- Binary still compiled with 12-line limit
- Took weeks to discover the mismatch

## Solution: Pre-Commit Hook for Binary Staleness

Add a pre-commit hook that detects when Swift package source files are being committed but binaries are stale.

### Hook Behavior

**Trigger Conditions:**
- Repository has `Package.swift` (is a Swift Package)
- Staging Swift files in `Sources/` directory
- `.build/release/` binaries exist

**Detection Logic:**
1. Find newest modified source file in `Sources/**/*.swift`
2. Find oldest binary file in `.build/release/`
3. Compare timestamps: `source_mtime > binary_mtime`
4. If stale → warn or block

### Configuration

Create `.stale-binary-check.yml` in package root:

```yaml
# Stale binary detection configuration
enabled: true
behavior: warn  # warn | block

# Packages that require blocking (not just warning)
critical: true  # Block commits if binaries are stale

# Optional: Custom rebuild command
rebuild_command: "swift build -c release"
```

### Behavior Modes

**WARN Mode** (exit 0 - allow commit):
```
⚠️  STALE BINARIES DETECTED

Package: swift-quality-tools
Source modified: 2025-11-13 17:26:15
Binary built:    2025-11-10 12:34:00

The binaries are older than the source you're committing.

Fix: swift build -c release

⚠️ Allowing commit but binaries should be rebuilt
```

**BLOCK Mode** (exit 1 - prevent commit):
```
🚨 STALE BINARIES - BLOCKING COMMIT

Package: swift-quality-tools (CRITICAL)

This package's binaries are used by hooks and other tools.
Committing stale source creates inconsistency.

Fix: swift build -c release

⛔ Commit blocked until binaries are rebuilt
```

## Implementation Plan

### Phase 1: Detection Script
Create `scripts/check-stale-binaries.sh`:
- Accept path to package directory
- Compare source vs binary timestamps
- Exit 0 (success) if fresh, 1 (failure) if stale
- Output formatted warning/error message

### Phase 2: Git Hook Integration
Add to synodic-hooks repository:
- `git/check_stale_binaries.py` - Python wrapper
- Called by `git/pre_commit.py` if repo is Swift Package
- Reads `.stale-binary-check.yml` for configuration
- Supports warn/block modes

### Phase 3: Documentation
- Update README.md with stale binary detection
- Add example `.stale-binary-check.yml`
- Document in CLAUDE-TOOLING.md

## Open Questions

1. **Default behavior**: Warn or block for all Swift packages?
   - Suggestion: Warn by default, block for critical packages

2. **Auto-rebuild**: Should hook offer to rebuild automatically?
   - Suggestion: No - just suggest command (keeps hook fast)

3. **Critical packages**: Which packages should block?
   - `swift-quality-tools` - definitely (used by all repos via hooks)
   - Others?

4. **Scope**: Check all binaries or only ones matching Sources/ edits?
   - Suggestion: All binaries (simpler, safer)

5. **Performance**: On large packages, is timestamp check fast enough?
   - Test with swift-quality-tools (should be instant)

## Dependencies

- Requires completed git hook infrastructure in synodic-hooks
- User mentioned "finish baking our new git hook setup" - what's needed?

## Related Issues

- Binary staleness caused 12 vs 15 line limit confusion
- Affects all Swift packages with compiled output
- Particularly critical for tools used by hooks

## Testing Strategy

1. **Manual Test**: Modify source, verify stale detection
2. **Fresh Build Test**: Rebuild, verify detection clears
3. **No Binary Test**: Fresh clone (no .build/), verify graceful handling
4. **Config Test**: Test warn vs block modes

## Future Enhancements

- Check if committed files are actually in staged commit
- Support other build systems (Xcode projects, Makefiles)
- Auto-rebuild option with user confirmation
- CI/CD integration to verify binaries in PRs

## Notes

- Keep hook fast (< 100ms) - only check timestamps
- Provide clear, actionable error messages
- Make it easy to bypass if needed (`git commit --no-verify`)
- Consider session caching to avoid repeated checks
