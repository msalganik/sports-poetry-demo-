# Refactor create_config skill using best practices

## Summary

The `create_config` skill (`.claude/skills/create_config/SKILL.md`) is a comprehensive configuration interface but could benefit from refactoring to improve maintainability, testability, and modularity.

## Current State

The skill is 852 lines containing:
- Conversation flow documentation
- Embedded Python code snippets
- Sport category mappings
- Error handling patterns
- Usage examples
- Best practices

**Strengths:**
- ✅ Comprehensive documentation
- ✅ Good error handling coverage
- ✅ Clear conversation flow
- ✅ Creates both config JSON and generator script

**Areas for Improvement:**
- ⚠️ **Violates 500-line guideline** (852 lines, should be <500)
- ⚠️ **Lacks progressive disclosure** - all details in one file instead of referenced files
- ⚠️ **Embedded code snippets** (hard to test/maintain, violates "utility scripts" pattern)
- ⚠️ **Hardcoded sport categories** (not extracted as reusable data)
- ⚠️ **Duplication of defaults** from config_builder.py
- ⚠️ **No evaluations** (violates evaluation-first development)

## Proposed Refactoring

### 1. Apply Progressive Disclosure Pattern (Split into Multiple Files)

Following Claude Code best practices: "SKILL.md serves as an overview that references detailed materials only when needed."

```
.claude/skills/create_config/
├── SKILL.md              # Main overview (~300 lines, under 500-line limit)
├── conversation_flow.md  # Detailed conversation steps (referenced from SKILL.md)
├── examples.md           # Usage examples (referenced from SKILL.md)
├── error_handling.md     # Error patterns and messages (referenced from SKILL.md)
├── sport_categories.json # Sport category mappings (loaded programmatically)
└── skill_helpers.py      # Utility script (pre-made, not generated)
```

**Note:** Tests go in repo-level `tests/` directory (not nested under skill):
```
tests/
├── test_config_builder.py     # Existing tests
└── test_create_config_skill.py # New skill evaluations
```

**Benefits:**
- ✅ Follows one-level-deep reference pattern
- ✅ SKILL.md provides overview, details loaded on-demand
- ✅ Filesystem acts as table of contents
- ✅ Easier to navigate and maintain
- ✅ Clear separation of concerns

### 2. Extract Sport Categories to JSON

Move hardcoded sport categories to `sport_categories.json`:

```json
{
  "winter_sports": ["hockey", "skiing", "snowboarding", "figure skating", "curling"],
  "ball_sports": ["basketball", "soccer", "tennis", "volleyball", "baseball"],
  "water_sports": ["swimming", "diving", "water polo", "surfing", "rowing"],
  ...
}
```

**Benefits:**
- Easy to extend without editing skill file
- Can be loaded programmatically
- Reusable across skills

### 3. Create Utility Script for Skill Logic

Following best practice: "Provide pre-made scripts instead of asking Claude to generate code—more reliable, saves tokens, ensures consistency."

Extract Python logic to `skill_helpers.py` as a **utility script** (not a class):

```python
# .claude/skills/create_config/skill_helpers.py
"""
Utility functions for create_config skill.

Claude should import and USE these functions directly rather than
reimplementing the logic. This saves tokens and ensures consistency.
"""

from pathlib import Path
from typing import Optional, Dict, List
import json
import re
import os

def load_sport_categories() -> Dict[str, List[str]]:
    """Load sport categories from sport_categories.json."""
    categories_path = Path(__file__).parent / "sport_categories.json"
    return json.loads(categories_path.read_text())

def check_api_key(provider: str) -> Optional[str]:
    """
    Check for API key in environment and .claude/claude.local.md.

    Returns: API key if found, None otherwise
    """
    # Check environment first
    env_var = "TOGETHER_API_KEY" if provider == "together" else "HUGGINGFACE_API_TOKEN"
    api_key = os.environ.get(env_var)
    if api_key:
        return api_key

    # Check .claude/claude.local.md
    local_config = Path.cwd() / ".claude" / "claude.local.md"
    if local_config.exists():
        content = local_config.read_text()
        pattern = f'{env_var}["\s:=]+([a-zA-Z0-9_-]+)'
        match = re.search(pattern, content)
        if match:
            return match.group(1)

    return None

def expand_sport_category(category: str) -> List[str]:
    """Expand category name to list of sports."""
    categories = load_sport_categories()
    category_key = category.lower().replace(" ", "_")
    return categories.get(category_key, [])

def create_generator_script(sports: List[str], mode: str, provider: str,
                           model: str, retry: bool, timestamp: str) -> str:
    """Generate Python script content using template pattern."""
    from string import Template

    # Template for generator script (using Template pattern from best practices)
    template = Template('''#!/usr/bin/env python3
"""
Configuration Generator Script
Generated: $generation_time
Sports: $sports_list
Mode: $mode
"""

from config_builder import ConfigBuilder
from pathlib import Path
from datetime import datetime

builder = ConfigBuilder.load_default()
builder.with_sports($sports_repr)
$mode_config
$retry_config

configs_dir = Path("output/configs")
configs_dir.mkdir(parents=True, exist_ok=True)
new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
new_config_path = configs_dir / f"config_{new_timestamp}.json"
builder.save(str(new_config_path))

print(f"✓ Configuration saved to: {new_config_path}")
''')

    # Build conditional sections
    mode_config = ""
    if mode == "llm":
        mode_config = f'''builder.with_generation_mode("llm")
builder.with_llm_provider("{provider}")
builder.with_llm_model("{model}")'''

    retry_config = "" if retry else "builder.with_retry(False)"

    return template.substitute(
        generation_time=timestamp,
        sports_list=", ".join(sports),
        sports_repr=repr(sports),
        mode=mode,
        mode_config=mode_config,
        retry_config=retry_config
    )
```

**Key principles applied:**
- ✅ **"Solve, Don't Punt"** - Explicit error handling, no magic numbers
- ✅ **Utility Scripts Pattern** - Pre-made functions, not generated code
- ✅ **Template Pattern** - Strict template for generator script creation
- ✅ **Saves tokens** - Claude imports and uses, doesn't reimplement

**Benefits:**
- Testable functions with clear contracts
- Reusable logic across skill invocations
- Type hints for reliability
- Self-documenting code

### 4. Reduce Duplication with config_builder.py

The skill duplicates default values that exist in `config_builder.py`. Instead:

```python
from config_builder import ConfigBuilder

# Get defaults from the builder, don't duplicate
defaults = ConfigBuilder.load_default().config
```

**Benefits:**
- Single source of truth
- No sync issues
- Automatic updates when defaults change

### 5. Create Evaluations (Evaluation-First Development)

Following best practice: "Create evaluations before extensive documentation. Build three representative test scenarios."

Create `tests/test_create_config_skill.py` with **three representative scenarios**:

```python
"""
Skill evaluations for create_config skill.

These tests measure skill effectiveness across common usage patterns.
Run before and after refactoring to ensure behavior is preserved.
"""

def test_scenario_1_quick_start_template_mode():
    """
    Scenario: User wants quick config with defaults.
    Input: "Create config for basketball, soccer, tennis"
    Expected: Template mode config created in <5 seconds
    """
    # Test sport category expansion
    # Test default mode selection
    # Test file creation (both JSON and generator script)

def test_scenario_2_llm_mode_with_api_key():
    """
    Scenario: User wants LLM mode with Together.ai.
    Input: "LLM mode with hockey, swimming, volleyball"
    Expected: API key found, LLM config created, generator script includes LLM settings
    """
    # Test API key detection (env or .claude/claude.local.md)
    # Test LLM provider/model defaults
    # Test generator script content

def test_scenario_3_category_expansion_error_recovery():
    """
    Scenario: User provides category, gets error, recovers.
    Input: "winter sports" → only 2 selected → add 1 more
    Expected: Category expands, validates count, suggests additions
    """
    # Test category expansion helper
    # Test validation error messages
    # Test recovery workflow

# Utility function tests
def test_load_sport_categories():
    """Test sport categories load from JSON correctly."""

def test_check_api_key_env():
    """Test API key detection from environment."""

def test_check_api_key_file():
    """Test API key detection from .claude/claude.local.md."""

def test_expand_sport_category():
    """Test 'winter sports' → ['hockey', 'skiing', ...]."""

def test_create_generator_script():
    """Test generator script template produces valid Python."""
```

**Evaluation-first workflow:**
1. Run these tests WITHOUT the refactored skill (establish baseline)
2. Measure failure modes (what doesn't work?)
3. Write minimal skill changes to pass tests
4. Iterate until all scenarios pass

**Benefits:**
- ✅ Follows evaluation-first development
- ✅ Three representative scenarios (best practice)
- ✅ Catch regressions during refactoring
- ✅ Document expected behavior
- ✅ Confidence in changes

### 6. Simplify Main SKILL.md

Keep only:
- Skill metadata (name, description)
- When to use
- High-level conversation flow
- Links to detailed docs

Move details to separate files:
- Detailed prompts → `conversation_flow.md`
- Examples → `examples.md`
- Error patterns → `error_handling.md`

**Benefits:**
- Quick overview without scrolling
- Details available when needed
- Easier onboarding

### 7. Improve Code Generation Template

Use a proper template system for generator script creation:

```python
from string import Template

GENERATOR_TEMPLATE = Template('''#!/usr/bin/env python3
"""
Configuration Generator Script
Generated: $generation_time
Output: $output_path

Parameters:
$parameters
"""

from config_builder import ConfigBuilder
from pathlib import Path
from datetime import datetime

$builder_code
''')
```

**Benefits:**
- Cleaner code
- Easier to maintain template
- Better formatting control

## Implementation Plan

### Phase 1: Extract and Organize (Low Risk)
1. Create `sport_categories.json`
2. Split documentation into separate markdown files
3. Update references in main SKILL.md

### Phase 2: Create Helper Module (Medium Risk)
4. Create `skill_helpers.py` with extracted functions
5. Add type hints and docstrings
6. Update skill to use helpers

### Phase 3: Add Tests (Low Risk)
7. Create test suite for helper functions
8. Add integration tests for skill behavior
9. Document test coverage

### Phase 4: Reduce Duplication (Medium Risk)
10. Remove hardcoded defaults
11. Load defaults from `config_builder.py`
12. Update documentation

### Phase 5: Template System (Low Risk)
13. Use `string.Template` for generator script
14. Clean up formatting
15. Add template tests

## Success Criteria

- [ ] Main SKILL.md under 300 lines
- [ ] All sport categories in JSON file
- [ ] Helper functions in separate module with tests
- [ ] No hardcoded defaults (load from config_builder)
- [ ] Generator script uses template system
- [ ] 80%+ test coverage of skill logic
- [ ] Documentation split into logical files
- [ ] All existing functionality preserved

## Non-Goals

- Changing conversation flow or user experience
- Modifying config_builder.py API
- Altering generated config file format

## Backward Compatibility

All changes should be backward compatible:
- Generated configs remain identical
- Same conversation flow
- Same error messages
- No breaking changes to orchestrator integration

## Estimated Effort

- Phase 1: 2-3 hours
- Phase 2: 3-4 hours
- Phase 3: 2-3 hours
- Phase 4: 1-2 hours
- Phase 5: 1-2 hours

**Total: 9-14 hours**

## Related Files

- `.claude/skills/create_config/SKILL.md` - Main skill file
- `config_builder.py` - Python API used by skill
- `tests/test_config_builder.py` - Existing tests

## Labels

`enhancement`, `refactoring`, `documentation`, `skills`
