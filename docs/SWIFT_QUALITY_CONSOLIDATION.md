# Swift Quality Toolchain Consolidation Strategy

## Executive Summary

This document defines the **comprehensive Swift quality enforcement architecture** across formatters, linters, custom rules, hooks, and the apple-platform-dev skill. It provides a clear classification framework for where each type of guidance belongs and a migration plan to consolidate the toolchain.

## Current State Analysis

### Tools Inventory

1. **SwiftFormat** (`swiftformat-smart`) - Automated code formatting
2. **SwiftLint** (`swiftlint-smart`) - Standard linting rules via config
3. **SwiftLint Custom** (`swiftlintcustom-smart`) - SwiftSyntax-based custom rules
4. **PostToolUse Hook** - Runs all three tools after edits, reports violations as errors
5. **PreToolUse Hook** - Blocks bare `swiftlint`/`swiftformat` commands, logs Swift edits
6. **CLAUDE-SWIFT.md** - 261 lines of procedural guidance and patterns
7. **apple-platform-dev skill** - 172 lines of workflow-oriented guidance with detailed references
8. **swift-edits.yml** - 619 recorded edit sessions showing real-world patterns

### Key Findings

From analysis of 619 Swift edit sessions:
- **Common patterns**: Extract to computed properties, use onChange(of:perform:), remove redundant code
- **Frequent violations**: Body line count, magic numbers, trailing commas
- **Workflow guidance**: "Drill baby drill" (process AGENT comments), batch editing suggestions
- **Architecture patterns**: MVVM+Manager, protocol-oriented design, extension-based organization

## The Classification Framework

### Decision Tree: Where Does a Rule Belong?

```
Is it automatically fixable without human judgment?
├─ YES → SwiftFormat (formatting tool)
│
└─ NO → Is it mechanically detectable via AST?
    ├─ YES → Is it SwiftUI/architecture-specific?
    │   ├─ YES → SwiftLint Custom (SwiftSyntax rules)
    │   └─ NO → SwiftLint Standard (config rules)
    │
    └─ NO → Does it require workflow context or judgment?
        ├─ Enforcement/blocking → Hook
        ├─ Procedural "how-to" → apple-platform-dev skill
        └─ Quick reference → CLAUDE-SWIFT.md (minimized)
```

## Tool-by-Tool Allocation

### 1. SwiftFormat (Auto-Formatting)
**Philosophy**: "If the computer can fix it deterministically, it should."

**Current Coverage** (shared-swiftformat.yml):
- Indentation, spacing, line breaks
- Trailing commas (modern Swift style)
- Import sorting with `@testable` grouping
- Redundant syntax removal (parens, returns, etc.)
- Brace/bracket/paren spacing
- Modifier ordering

**Add to SwiftFormat**:
- None needed - excellent coverage already

**Keep Out**:
- Anything requiring semantic understanding (e.g., "is this a magic number?")
- Architecture decisions (e.g., "should this be extracted?")

### 2. SwiftLint Standard (Configuration-Based Rules)
**Philosophy**: "Mechanical detection of code smells via pattern matching."

**Current Coverage** (shared-swiftlint.yml):
- Metrics (line length, file length, function complexity)
- Performance patterns (isEmpty vs count == 0)
- Safety patterns (unhandled throwing tasks)
- Code quality (no magic numbers, toggle vs manual flip)
- File organization (one declaration per file)

**Add to SwiftLint**:
- None needed - conservative basic set is appropriate

**Keep Out**:
- SwiftUI-specific rules (use SwiftSyntax instead)
- Deep AST analysis (too complex for regex)

### 3. SwiftLint Custom (SwiftSyntax Rules)
**Philosophy**: "Deep AST analysis for architecture and SwiftUI patterns."

**Current Coverage** (test-custom-rule.swift):
1. `skimmable_body` - View body ≤15 lines
2. `no_group_body` - No top-level Group (unless has modifiers)
3. `one_top_level_view` - Exactly one top-level view in body
4. `excessive_nesting` - Max 4 levels of indentation depth

**Add to SwiftLint Custom** (from CLAUDE-SWIFT.md patterns):

**High Priority**:
1. **`view_structure_order`** - Enforce View property ordering:
   - Embedded types first
   - Environment properties grouped
   - Other properties
   - init before body
   - body
   - Computed properties/methods after

2. **`no_wrapper_body`** - Detect pointless wrapper properties:
   ```swift
   // BAD
   var body: some View { mainContent }
   private var mainContent: some View { VStack {...} }
   ```

3. **`constants_enum_usage`** - Detect magic numbers, suggest Constants enum

4. **`blank_line_import_separation`** - Enforce blank line between regular imports and @testable imports

**Medium Priority**:
5. **`frame_alignment_parameters`** - Frame with alignment must have width/height
6. **`multiline_arguments_threshold`** - Functions with 4+ args on multiple lines
7. **`no_modifier_after_closing_delimiter`** - No `.modifier` on same line as `)`/`]`

**Low Priority** (consider if valuable):
8. **`prefer_frame_over_spacer`** - Frame with alignment over VStack+Spacer
9. **`no_if_modifier`** - Detect custom `.if` modifier usage

**Keep Out**:
- Anything that's purely educational (belongs in skill)
- Context-dependent refactoring advice

### 4. PostToolUse Hook
**Philosophy**: "Automatic enforcement and helpful guidance after edits."

**Current Behavior**:
- Runs all three Swift quality tools after Edit operations
- Reports violations as ERRORS (ensures Claude's attention)
- Adds context-specific hints (e.g., enum Constants pattern)
- Suggests batch editing after 3 Swift file edits

**Keep In Hook**:
- Running quality tools automatically
- Formatting violations as errors
- Adding violation-specific hints
- Performance optimization suggestions

**Remove From Hook**:
- Nothing - current implementation is ideal

**Future Enhancement**:
- Add more context-specific hints based on violation types
- Consider file-specific hint suppression (e.g., don't show Constants hint in test files)

### 5. PreToolUse Hook
**Philosophy**: "Block bad practices before they happen."

**Current Behavior**:
- Blocks bare `swiftlint`/`swiftformat` commands (enforces -smart usage)
- Blocks commits to non-claude/* branches
- Logs Swift file edits to swift-edits.yml

**Keep In Hook**:
- All current blocking behaviors
- Swift edit logging (valuable for pattern analysis)

**Add to Hook**:
- Consider blocking other anti-patterns if they emerge

### 6. apple-platform-dev Skill
**Philosophy**: "Procedural workflow guidance for active development."

**Current Coverage**:
- The 12-line body rule workflow (now 15 via linter, but skill says 12)
- Five refactoring strategies (computed properties, handlers, components, etc.)
- View structure order enforcement
- Testing standards (Swift Testing only)
- Architecture patterns (MVVM+Manager)
- Common error patterns

**Update in Skill**:
1. **Change "12-line body rule" to "15-line body rule"** - align with linter
2. **Add SwiftSyntax rule identifiers** for reference:
   - `skimmable_body` - body line count
   - `no_group_body` - no top-level Group
   - `one_top_level_view` - exactly one top-level view
   - `excessive_nesting` - max 4 indentation levels
   - (Add new rules as implemented)

3. **Add "When You See a Violation" workflow**:
   ```
   When you see a SwiftSyntax violation:
   1. Read the violation message for the rule identifier
   2. Apply the appropriate refactoring strategy:
      - skimmable_body → Five refactoring strategies
      - no_group_body → Replace Group with proper container
      - one_top_level_view → Wrap multiple views in VStack/HStack/ZStack
      - excessive_nesting → Extract complex logic to functions/properties
   3. Verify fix resolves the violation
   ```

4. **Expand "Common Patterns" section** with insights from swift-edits.yml:
   - onChange patterns (direct function reference, zero-param closures)
   - Computed property extraction patterns
   - AGENT comment processing workflow
   - Preview creation patterns

**Keep In Skill**:
- All procedural "how to do X" guidance
- Architecture decision frameworks
- Testing patterns and workarounds
- Platform-specific patterns (Metal, Core Data)

**Remove From Skill**:
- Nothing - current scope is appropriate

### 7. CLAUDE-SWIFT.md
**Philosophy**: "Quick reference for critical reminders and non-automatable guidance."

**Current State**: 261 lines - too much overlap with skill

**CONSOLIDATION TARGET**: Reduce to ~100 lines

**Keep in CLAUDE-SWIFT.md** (Critical Reminders Only):
1. **Compiler Warnings** - CRITICAL section (essential)
2. **Swift Quality Tools** - -smart enforcement (essential)
3. **Batch Editing** - Performance optimization (essential)
4. **Testing** - Swift Testing only (essential)
5. **Imports** - Blank line between regular/@testable (essential until in linter)
6. **Optionals** - Shorthand binding pattern (quick reference)
7. **SwiftUI Body** - NEVER wrapper properties (anti-pattern warning)
8. **Constants** - enum Constants pattern (quick reference)
9. **onChange Patterns** - Direct reference vs closures (quick reference)
10. **Code Quality Philosophy** - When to invoke "code quality over limits" (judgment call)

**MOVE to apple-platform-dev skill** (Procedural Guidance):
- SwiftUI style patterns (detailed refactoring strategies)
- SwiftUI best practices (frame over spacer, etc.)
- Body refactoring patterns (five strategies)
- View structure order (detailed explanation)
- Arguments and methods formatting
- General code quality principles
- Package modularization workflow
- Common error patterns (ClosedRange, AppStorage, etc.)

**REMOVE entirely** (Already enforced by tools):
- Rules already in SwiftLint/SwiftFormat (trailing commas, etc.)
- Patterns enforced by SwiftSyntax rules (body line count, etc.)

## Migration Plan

### Phase 1: Immediate ✅ COMPLETED
1. ✅ Create this consolidation document
2. ✅ Create /sc:classify-swift-rule command
3. ✅ Update SWIFT_QUALITY_CONSOLIDATION.md with decision tree examples

### Phase 2: SwiftSyntax Rule Implementation ✅ COMPLETED
1. ✅ Implement high-priority SwiftSyntax rules:
   - `view_structure_order`
   - `no_wrapper_body`
   - `constants_enum_usage`
   - `blank_line_import_separation`
   - `preview_required` (added during implementation)

2. ✅ Refactor into modular structure for maintainability
3. ✅ Test on gravity-well project
4. ✅ Verify hook integration works correctly

### Phase 3: Documentation Consolidation ✅ COMPLETED
1. ✅ Update apple-platform-dev skill:
   - ✅ Change 12-line → 15-line body rule
   - ✅ Add SwiftSyntax rule identifier reference
   - ✅ Add "When You See a Violation" workflow
   - ✅ Document enforcement via swiftlintcustom-smart

2. ✅ Reduce CLAUDE-SWIFT.md to 157 lines (40% reduction):
   - ✅ Keep critical reminders only (10 core sections)
   - ✅ Move procedural guidance to skill
   - ✅ Remove tool-enforced rules

3. ⏭️ Update skill references/ files with detailed patterns (deferred to future)

### Phase 4 Alpha: Preference Discovery Framework ✅ COMPLETED
**Purpose**: Extract unstated preferences through deliberate code examples

**Implementation**:
1. ✅ Created PreferenceDiscovery.swift with 52 edge cases across 6 categories:
   - A. Property wrapper ordering (8 examples)
   - B. View body edge cases (10 examples)
   - C. Naming conventions (10 examples)
   - D. Constants patterns (8 examples)
   - E. Architecture boundaries (10 examples)
   - F. Preview patterns (6 examples)

2. ✅ Created PREFERENCE_TRACKING.md decision recording template:
   - Accept / Reject / Context-Dependent framework
   - Reasoning capture
   - Confidence rating (Strong / Moderate / Weak)
   - Implementation path mapping (SwiftSyntax / Skill / CLAUDE-SWIFT / None)

3. ✅ Created SESSION_GUIDE.md facilitation guide:
   - 90-120 minute structured session
   - Recording best practices
   - Decision quality criteria
   - Implementation criteria
   - Post-session action plan
   - Success metrics

4. ✅ Created comprehensive README.md with methodology

**Deliverables**:
- PreferenceDiscovery.swift (52 edge cases)
- PREFERENCE_TRACKING.md (structured template)
- SESSION_GUIDE.md (complete facilitation guide)
- README.md (quick start + methodology)

**Next Steps** (Deferred to Future Session):
1. ⏭️ Conduct preference discovery session (90-120 minutes)
2. ⏭️ Implement 2-5 new SwiftSyntax rules from strong preferences
3. ⏭️ Update apple-platform-dev skill with decision frameworks
4. ⏭️ Add critical reminders to CLAUDE-SWIFT.md
5. ⏭️ Create test suite from discovered patterns

**Research Foundation**:
- Preference elicitation methodologies (choice-based queries, ~10 query sessions)
- Edge case discovery techniques (boundary testing, equivalence partitioning)
- Pattern mining strategies (frequency analysis, expert curation)
- UX research methods (qualitative probing, confidence rating)

### Phase 4 Beta: Continuous Improvement (Ongoing)
1. Monitor swift-edits.yml for new patterns
2. Use /sc:classify-swift-rule command for new situations
3. Add rules incrementally as patterns emerge
4. Update skill with new workflows as discovered
5. Periodic preference discovery sessions (quarterly?)

## Success Metrics

**Consolidation Complete When**:
1. ✅ All automatically fixable patterns → SwiftFormat
2. ✅ All mechanically detectable patterns → SwiftLint or SwiftSyntax
3. ✅ All procedural guidance → apple-platform-dev skill
4. ✅ CLAUDE-SWIFT.md ≤ 100 lines (critical reminders only)
5. ✅ Clear decision tree for future rule classification
6. ✅ No duplication between documents

**Quality Maintained When**:
1. All 619 edit patterns from swift-edits.yml codified somewhere
2. No regressions in code quality enforcement
3. Claude can find guidance quickly (< 10 seconds)
4. New rules have clear home via classification command

## Future Considerations

### Potential Tool Additions
1. **Swift Testing Integration** - Custom rules for test patterns
2. **Architecture Linter** - Detect MVVM violations, improper Manager usage
3. **Dependency Analyzer** - Detect circular dependencies, improper imports
4. **Performance Linter** - Detect common performance anti-patterns

### Skill Enhancements
1. **Interactive Refactoring Workflows** - Step-by-step guided refactoring
2. **Pattern Library** - Searchable examples from swift-edits.yml
3. **Architecture Decision Records** - Why we chose specific patterns

### Hook Enhancements
1. **Smart Hint Suppression** - Don't show hints in test files
2. **Violation Trends** - Track common violations to inform new rules
3. **Auto-Fix Suggestions** - Propose specific fixes for common violations

## Appendix: Real-World Pattern Examples

### From swift-edits.yml Analysis (619 entries)

**Most Common Patterns**:
1. Extract computed properties to reduce body line count
2. Use `onChange(of:perform:)` direct function reference
3. Remove redundant modifiers and code
4. Process AGENT comments for refactoring hints
5. Create previews for new components
6. Extract complex closures to handler functions
7. Use Constants enum for magic numbers
8. Simplify Binding creation with computed properties

**Anti-Patterns Caught**:
1. Pointless wrapper properties (`var body: some View { mainContent }`)
2. Custom `.if` modifier usage
3. Group as top-level view without modifiers
4. Magic numbers in view code
5. Complex inline closures in view builders
6. Missing blank lines between imports
7. Excessive indentation (> 4 levels)

**Workflow Insights**:
- "Drill baby drill!" → Process all AGENT comments systematically
- Batch editing suggested after 3 Swift file edits
- Extract-first approach: computed properties before component extraction
- Preview-driven development: Always add preview after creating component

## Decision Tree Examples

### Example 1: "Trailing Commas"
```
Q: Where should trailing comma enforcement live?
A: SwiftFormat
   - Automatically fixable? YES ✓
   - No human judgment needed
   - Already implemented in shared-swiftformat.yml
```

### Example 2: "Body Line Count > 15"
```
Q: Where should body line count limit live?
A: SwiftLint Custom (SwiftSyntax)
   - Automatically fixable? NO ✗
   - Mechanically detectable? YES ✓
   - SwiftUI-specific? YES ✓
   - Requires AST analysis (not just regex)
   - Already implemented: skimmable_body rule
```

### Example 3: "When to Extract Computed Property vs Component"
```
Q: Where should extraction strategy guidance live?
A: apple-platform-dev skill
   - Automatically fixable? NO ✗
   - Mechanically detectable? NO ✗
   - Requires workflow context? YES ✓
   - Needs human judgment on complexity/reusability
   - Procedural guidance with examples
```

### Example 4: "Enforce -smart Tool Usage"
```
Q: Where should -smart enforcement live?
A: PreToolUse Hook
   - Enforcement/blocking? YES ✓
   - Prevents bad practice before it happens
   - Already implemented with helpful error messages
```

### Example 5: "Report Violations Clearly"
```
Q: Where should violation reporting live?
A: PostToolUse Hook
   - Runs after edits? YES ✓
   - Adds context-specific hints
   - Formats violations as errors for Claude's attention
   - Already implemented with excellent UX
```
