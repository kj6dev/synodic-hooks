# Session Files - Always Commit

## Critical Policy

**ALWAYS commit `.claude/sessions/*.yml` files with your code changes.**

## Why Commit Session Files?

Session files document the **intent** behind code changes:
- **User prompts** that drove each edit
- **Change classification** (refactor, bugfix, feature, docs, style, test)
- **Code diff context** showing what changed and why
- **Audit trail** of AI-assisted development

## Benefits

**For Future Claude Sessions:**
- Understands historical context and reasoning
- Learns patterns from previous work
- Avoids repeating past mistakes
- Builds on established conventions

**For Pattern Analysis:**
- Training data for skill development
- Refactoring pattern detection
- Code quality metrics over time
- Preference discovery and rule extraction

**For Team Context:**
- Documents AI-assisted changes
- Provides rationale for code reviews
- Creates searchable development history
- Enables better collaboration

## Git Workflow

```bash
# Session files should be committed WITH the code they document
git add .
git commit -m "feat: implement user authentication

Includes session file documenting prompts and refactoring decisions."
```

## Multiple Projects

Each repository maintains its own `.claude/sessions/` directory:
- Sessions log edits in the repo WHERE FILES ARE EDITED
- Multiple projects can commit independently
- No conflicts between different repositories

## This File

This CLAUDE.md is automatically synced from the hooks repository template to ensure consistent documentation across all projects.
