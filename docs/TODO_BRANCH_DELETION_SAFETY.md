# TODO: Branch Deletion Safety for Unmerged Work

## Problem

SessionStart hook currently cleans up empty and merged claude/* branches, but there's no safeguard against **manual branch deletion** of unmerged work. This led to loss of valuable commits when `claude/20251113202538` was deleted before being merged to develop.

**What was lost:**
- 30 commits with unmerged work
- Swift quality tools command (`/sy:swift-quality-tools`)
- Apple platform skill expansion (342 lines)
- Session files documenting all the work (1,179 lines)
- `.gitignore` fix removing `.claude/` entry

All work was recovered via git reflog and cherry-picking, but this shouldn't have happened.

## Current Hook Behavior (Correct)

The SessionStart hook in `claude/session/branch_management.py` has the **correct** logic:

```python
def cleanup_empty_branches(repo_path: str):
    # Only deletes if EMPTY (zero commits)
    if is_empty_claude_branch(branch, repo_path):
        delete_branch(...)

    # Only deletes if MERGED
    if is_merged_claude_branch(branch, repo_path):
        delete_branch(...)
```

**The hook is innocent** - it only deletes empty or merged branches as designed.

## Root Cause

User asked Claude to clean up branches via prompt. Claude deleted `claude/20251113202538` **without checking merge status**, even though the user's instructions said "only remove merged branches".

This was human error by the AI, not a hook bug.

## Proposed Solutions

### Option 1: Pre-Delete Warning Hook
Add a hook that runs before branch deletion to warn about unmerged work:

**Implementation:**
- New hook: `PreBranchDelete` (if Claude Code supports this)
- Check merge status before allowing deletion
- Block deletion if branch has unmerged commits
- Show list of commits that would be lost

**Pros:**
- Prevents accidents at the source
- Works for both manual and automated deletions

**Cons:**
- May not be supported by Claude Code hook system
- Could be overly aggressive (sometimes you DO want to delete unmerged branches)

### Option 2: SessionStart Unmerged Branch Report
Add a section to SessionStart that reports unmerged claude/* branches:

**Implementation:**
- After cleanup, check for remaining claude/* branches
- Run `git branch --no-merged develop` for each
- Emit warning if any unmerged branches exist
- Suggest reviewing or merging them

**Example Output:**
```
⚠️ Unmerged claude/* branches detected:
  - claude/20251113202538 (30 commits ahead of develop)
  - claude/20251110160352 (5 commits ahead of develop)

💡 Review these branches and merge or delete them:
   git checkout claude/20251113202538
   git log develop..HEAD  # Review commits
   gh pr create           # Create PR if valuable
   git branch -D ...      # Or force delete if unwanted
```

**Pros:**
- Non-intrusive reminder
- Helps you notice forgotten branches
- Doesn't block workflow

**Cons:**
- Doesn't prevent deletion
- Could become noise if ignored

### Option 3: Slash Command for Safe Branch Cleanup
Create `/sy:cleanup-branches` command that:
- Lists all claude/* branches with merge status
- Shows commit counts for each
- Only deletes merged branches
- Asks for confirmation before deleting
- Never touches unmerged branches

**Implementation:**
```markdown
# /sy:cleanup-branches

1. Find all claude/* branches
2. Check merge status for each against develop/main
3. Show report:
   - Merged branches (safe to delete)
   - Unmerged branches (keep)
   - Empty branches (safe to delete)
4. Delete only merged/empty branches
5. Report what was deleted
```

**Pros:**
- Explicit, user-initiated action
- Clear report before deletion
- Prevents accidental deletions
- Can be run anytime

**Cons:**
- Requires user to remember to run it
- Doesn't help with manual `git branch -D` commands

### Option 4: Combination Approach
Implement both Option 2 (warning in SessionStart) and Option 3 (cleanup command):

**SessionStart Hook:**
- Warn about unmerged branches at session start
- Suggest using `/sy:cleanup-branches` if cleanup needed

**Cleanup Command:**
- Safe, explicit cleanup when user wants it
- Only touches merged/empty branches

**Pros:**
- Best of both worlds
- Non-intrusive warnings + safe cleanup tool

**Cons:**
- More code to maintain

## Recommendations

**Immediate (Option 3):** Create `/sy:cleanup-branches` command for safe, explicit cleanup.

**Future (Option 2):** Add unmerged branch warning to SessionStart hook to raise awareness.

**Maybe (Option 1):** Investigate if Claude Code supports PreBranchDelete hooks.

## Implementation Notes

- Hook cleanup logic is already correct - no changes needed
- Focus on preventing **manual** deletion mistakes
- Session files provide recovery path if deletion still happens
- Git reflog is the ultimate safety net (30-90 days retention)

## Related Files

- `claude/session/branch_management.py` - Existing cleanup logic
- `shared/git/claude.py` - Branch detection utilities
- `claude/session_start.py` - Entry point for SessionStart hook

## Status

**Not yet implemented** - Captured for future development.
