# TODO: Claude Branch Strategy Improvement

## Concept

Replace timestamp-based branch generation with a persistent branching model for Claude Code work.

## Proposed Structure

### Primary Branch
- **`claude`** - Persistent main branch for all Claude Code work
- Replaces auto-generated timestamp-based branches
- Long-lived, not ephemeral

### Feature Branches (Optional)
- **`claude/feature-a`** - Named feature branches under `claude/`
- **`claude/feature-b`** - Additional features as needed
- Human-readable, purposeful names instead of timestamps
- Created when logical separation is needed

## Cross-Repo Editing Behavior

When Claude Code is running in one repository but making changes to files in a different repository:

### Default Behavior
- Changes default to the **`claude`** branch in the target repository
- No special configuration needed
- Provides consistent location for Claude's work

### Optional Override
- Optionally target a specific named feature branch (e.g., `claude/refactor-hooks`)
- Allows logical grouping of related changes across repos
- User can specify which feature branch to use

## Benefits

1. **Predictable**: Always know where Claude's changes are (`claude` branch)
2. **Persistent**: `claude` branch remains for ongoing work (not deleted after merge)
3. **Organized**: Feature branches provide logical grouping when needed
4. **Human-Readable**: `claude/add-logging` vs `claude-20251116-105715`
5. **Multi-Repo**: Consistent strategy when working across repositories

## Implementation Considerations

- [ ] How to configure default branch per repo?
- [ ] Hook integration for automatic branch switching?
- [ ] Conflict resolution when `claude` branch exists with changes?
- [ ] Convention for naming `claude/*` feature branches?
- [ ] PR workflow - merge feature branches to `claude`, then `claude` to `develop`/`main`?
- [ ] Session persistence - track which branch was used?

## Questions

- Should `claude` branch auto-merge to `develop`/`main` or require manual PR?
- What's the cleanup strategy for `claude/*` feature branches?
- How to handle work that spans multiple repositories with different feature needs?
- Should hooks enforce this naming convention?

## Status

**Not yet implemented** - Capturing idea for future development.
