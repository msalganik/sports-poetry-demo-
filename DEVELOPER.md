# Developer Guide

This guide is for developers who want to understand, modify, or extend the sports poetry demo.

For basic usage, see [README.md](README.md). For configuration details, see [CONFIG_GUIDE.md](CONFIG_GUIDE.md).

## Table of Contents

- [Architecture](#architecture)
- [File Structure](#file-structure)
- [Logging System](#logging-system)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Customization](#customization)
- [Advanced Usage](#advanced-usage)
- [Learning Points](#learning-points)
- [Next Steps](#next-steps)

## Architecture

### Four-Layer Design

This demo separates concerns across four distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: 👤 USER & 🤖 CLAUDE CODE (Configuration)           │
│                                                              │
│  👤 User: "I want poems about baseball, basketball, football"│
│    ↓                                                         │
│  🤖 Claude: Validates sports list (3-5 required)             │
│            Creates timestamped config file                   │
│            Checks API keys (if LLM mode)                     │
│    ↓                                                         │
│  📄 output/configs/config_20251103_225304.json               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: 🐍 PYTHON ORCHESTRATION (Workflow Management)      │
│                                                              │
│  🐍 orchestrator.py:                                         │
│    • Reads config file                                       │
│    • Generates unique session_id                             │
│    • Creates session directory                               │
│    • Copies config to session directory                      │
│    • Creates config.changelog.json                           │
│    • Launches N poetry agents in parallel (ThreadPool)      │
│    • Monitors completion/failures                            │
│    • Retries failed agents (optional)                        │
│    • Waits for all agents to complete                        │
│    • Launches analyzer agent (sequential)                    │
│    • Writes provenance logs (execution_log.jsonl)           │
│    • Writes usage analytics (usage_log.jsonl)               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: 🐍 POETRY AGENTS (Parallel Poem Generation)        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 🐍 poetry_agent│ │ 🐍 poetry_agent│ │ 🐍 poetry_agent│  │
│  │   (baseball) │  │ (basketball) │  │  (football)  │     │
│  │              │  │              │  │              │     │
│  │ • Generate   │  │ • Generate   │  │ • Generate   │     │
│  │   haiku      │  │   haiku      │  │   haiku      │     │
│  │ • Generate   │  │ • Generate   │  │ • Generate   │     │
│  │   sonnet     │  │   sonnet     │  │   sonnet     │     │
│  │ • Write      │  │ • Write      │  │ • Write      │     │
│  │   metadata   │  │   metadata   │  │   metadata   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  All agents run in parallel via ThreadPoolExecutor          │
└─────────────────────────────────────────────────────────────┘
                          ↓
            (wait for all to complete)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: 🐍 ANALYZER AGENT (Sequential Synthesis)           │
│                                                              │
│  🐍 analyzer_agent.py:                                       │
│    • Reads all generated poems from Layer 3                  │
│    • Reads execution_log.jsonl for workflow stats            │
│    • Validates form adherence (haiku = 3 lines, etc.)       │
│    • Compares content across sports                          │
│    • Identifies missing sports (if any failed)               │
│    • Writes analysis_report.md                               │
│                                                              │
│  Runs AFTER all poetry agents complete                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   OUTPUT FILES:
          output/session_YYYYMMDD_HHMMSS_xxxxxx/
            ├── baseball/haiku.txt, sonnet.txt, metadata.json
            ├── basketball/haiku.txt, sonnet.txt, metadata.json
            ├── football/haiku.txt, sonnet.txt, metadata.json
            ├── analysis_report.md
            ├── config.json
            ├── config.changelog.json
            ├── execution_log.jsonl
            └── usage_log.jsonl
```

### Responsibility Breakdown

| Component | Role | Language | Execution Model | Key Responsibilities |
|-----------|------|----------|----------------|---------------------|
| 👤 **User** | Input provider | Natural language | Interactive | Specify 3-5 sports, choose generation mode |
| 🤖 **Claude Code** | Config builder | Python (via skill) | Interactive | Validate input, create timestamped config, check API keys |
| 🐍 **orchestrator.py** | Workflow coordinator | Python | Sequential | Launch agents, manage retries, coordinate layers, log everything |
| 🐍 **poetry_agent.py** | Worker (subprocess) | Python | **Parallel** | Generate haiku + sonnet for one sport |
| 🐍 **analyzer_agent.py** | Synthesizer | Python | **Sequential** (after Layer 3) | Compare all poems, create final report |

### Two Paths to Configuration

**Path A: 👤 Conversational (User + Claude)**
```
👤 User: "baseball, basketball, football with LLM mode"
  → 🤖 Claude validates & creates: output/configs/config_20251103_225304.json
  → 🐍 Run: python3 orchestrator.py --config output/configs/config_20251103_225304.json
```

**Path B: 🐍 Direct Python API (Scripting/Automation)**
```python
from config_builder import ConfigBuilder
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ConfigBuilder() \
    .with_sports(['baseball', 'basketball', 'football']) \
    .with_generation_mode('llm') \
    .save(f'output/configs/config_{timestamp}.json')
# Then run: python3 orchestrator.py --config output/configs/config_TIMESTAMP.json
```

Both paths produce identical config files and identical workflow execution.

### Key Design Patterns

1. **Parallel Execution**: Agents run simultaneously via `concurrent.futures.ThreadPoolExecutor` (orchestrator.py:267)
2. **Graceful Degradation**: Failed agents don't stop the workflow; orchestrator continues with successful ones
3. **Session Isolation**: Each run creates a unique session directory under `output/{session_id}/`
4. **Provenance Logging**: Every action logged to `execution_log.jsonl` with timestamps via ProvenanceLogger class
5. **Thread Safety**: ProvenanceLogger uses threading.Lock for concurrent writes (orchestrator.py:27)

### Agent Communication

Agents are spawned as subprocesses (not threads):
- **Parent**: orchestrator.py
- **Child**: poetry_agent.py (one per sport)
- **Communication**: Command-line args, file I/O, and exit codes
- **Timeout**: 120 seconds per agent (orchestrator.py:156)

### Important Implementation Details

1. **Session Directory Creation**: Happens after config read (orchestrator.py:493) to ensure session_id is available
2. **Config Copy**: Full config file copied to session directory (orchestrator.py:497-504) for self-contained sessions
3. **Log File Migration**: Early logs from root are moved to session directory (orchestrator.py:515-523)
4. **Symlink Management**: `output/latest` always points to most recent session (orchestrator.py:124-127)
5. **Metadata Tracking**: Each agent writes metadata.json with line counts, word counts, duration (poetry_agent.py:379-394)

## File Structure

### Input Files
- `output/configs/config_TIMESTAMP.json` - Timestamped config created by create_config skill or ConfigBuilder
- `config.default.json` - Default configuration template (checked into git)

### Core Scripts
- `orchestrator.py` - Main coordinator that launches agents and manages workflow
- `poetry_agent.py` - Generates haiku + sonnet for one sport (runs as subprocess)
- `analyzer_agent.py` - Synthesizes results and creates final report
- `config_builder.py` - Configuration builder with validation API

### Output Files (per session)
- `output/{session_id}/config.json` - Full configuration copy (session-specific)
- `output/{session_id}/config.changelog.json` - Configuration changes vs default
- `output/{session_id}/{sport}/haiku.txt` - Generated haikus
- `output/{session_id}/{sport}/sonnet.txt` - Generated sonnets
- `output/{session_id}/{sport}/metadata.json` - Poem metadata (line counts, word counts, timestamps)
- `output/{session_id}/analysis_report.md` - Final comparative analysis
- `output/{session_id}/execution_log.jsonl` - Detailed provenance (every action)
- `output/{session_id}/usage_log.jsonl` - Aggregate analytics (per run)
- `output/latest` - Symlink to most recent session directory

### Configuration System

The system uses a two-location pattern for config files:

1. **Input Location**:
   - `output/configs/config_TIMESTAMP.json` - Timestamped configs created by the skill or ConfigBuilder
   - Used by orchestrator via `--config` flag (required)

2. **Session Copy** (automatic):
   - Orchestrator copies input config to `output/{session_id}/config.json`
   - Makes each session self-contained and reproducible
   - Logged in execution_log.jsonl as `config_copied` event

**Self-contained sessions**: Each session directory contains everything needed to understand/reproduce the run:
- `config.json` - Full configuration used
- `config.changelog.json` - What changed from default
- `execution_log.jsonl` - Complete audit trail
- `{sport}/` - Generated poems and metadata

## Logging System

### execution_log.jsonl (Detailed Provenance)

One event per line, showing exact actor, action, and timing:

```json
{"timestamp": 1730476980.123, "timestamp_iso": "2025-11-01T13:03:00Z", "actor": "orchestrator", "action": "read_config", "message": "Reading configuration file"}
{"timestamp": 1730476980.234, "actor": "orchestrator", "action": "config_loaded", "details": {"sports": ["basketball", "soccer", "tennis"], "sports_count": 3}}
{"timestamp": 1730476980.345, "actor": "orchestrator", "action": "launch_agent", "details": {"sport": "basketball", "attempt": 1}}
{"timestamp": 1730476982.456, "actor": "agent_basketball", "action": "complete", "details": {"duration_s": 2.1, "haiku_lines": 3, "sonnet_lines": 14}}
```

**Use cases:**
- Debug which agent failed and when
- Prove which agent created which file
- Reconstruct exact execution timeline
- Identify performance bottlenecks

### usage_log.jsonl (Aggregate Analytics)

One entry per workflow run:

```json
{
  "session_id": "abc123",
  "timestamp": "2025-11-01T13:03:00Z",
  "sports": ["basketball", "soccer", "tennis"],
  "sports_count": 3,
  "agents_launched": 3,
  "agents_succeeded": 3,
  "agents_failed": 0,
  "agent_results": [
    {"sport": "basketball", "status": "success", "duration_s": 2.1},
    {"sport": "soccer", "status": "success", "duration_s": 2.3},
    {"sport": "tennis", "status": "success", "duration_s": 1.9}
  ],
  "total_duration_s": 8.4,
  "errors": []
}
```

**Use cases:**
- Analyze failure patterns over time
- Track most popular sports
- Measure performance trends
- Identify systematic issues

### Configuration Changelog

Location: `output/{session_id}/config.changelog.json`

Tracks what changed from the default configuration:

```json
{
  "timestamp": "2025-11-03T18:40:00.123456+00:00",
  "session_id": "session_20251103_184000_a3f9c2",
  "user": "orchestrator",
  "reason": "Workflow execution",
  "changed_from_default": ["sports", "generation_mode", "llm"],
  "changes": {
    "sports": {
      "old": ["basketball", "soccer", "tennis"],
      "new": ["hockey", "swimming", "volleyball"]
    },
    "generation_mode": {
      "old": "template",
      "new": "llm"
    }
  }
}
```

**Key design:**
- Changelog is created by the **orchestrator** at runtime, not by ConfigBuilder
- Compares against `config.default.json` only (stable baseline)
- "old" = value from default template
- "new" = value in current config
- All timestamps use ISO 8601 format exclusively

### Querying Logs with jq

**View execution log:**
```bash
cat output/latest/execution_log.jsonl | jq .
```

**Find all failures:**
```bash
cat output/latest/execution_log.jsonl | jq 'select(.action == "failed")'
```

**View configuration changelog:**
```bash
cat output/latest/config.changelog.json | jq .
```

**Quick scan - what changed from default:**
```bash
cat output/latest/config.changelog.json | jq .changed_from_default
```

**Find sessions where sports changed:**
```bash
find output -name "config.changelog.json" -exec jq 'select(.changed_from_default | contains(["sports"]))' {} \;
```

**Summary of all changes across sessions:**
```bash
find output -name "config.changelog.json" -exec jq '{session: .session_id, changed: .changed_from_default, user: .user, reason: .reason}' {} \;
```

**Get exact old/new values for specific changes:**
```bash
find output -name "config.changelog.json" -exec jq 'select(.changes.sports) | {session: .session_id, sports: .changes.sports}' {} \;
```

## Error Handling

The workflow uses **graceful degradation**:

1. Each agent runs once
2. If it fails, optionally retry once (configurable)
3. Continue with other agents regardless of individual failures
4. Log all failures with full details
5. Analyzer notes missing sports in final report

**Example with failure:**

```bash
# Agent for "hockey" fails
[orchestrator] Launching poetry agent for hockey (attempt 1)
[agent_hockey] failed: FileNotFoundError...
[orchestrator] Retrying hockey agent
[agent_hockey] failed: FileNotFoundError...
[orchestrator] All agents complete: 2 succeeded, 1 failed

# Workflow continues, analyzer notes the gap
# Logs capture exactly what happened
```

### Retry Behavior

The orchestrator supports optional retries (orchestrator.py:62):
- Default: `retry_enabled=True`
- Each failed agent gets one retry attempt
- Can be disabled in configuration or by modifying SportsPoetryOrchestrator initialization

## Testing

### Test Structure

Tests are organized by component:
- `test_orchestrator.py`: Workflow coordination tests
- `test_poetry_agent.py`: Individual agent tests
- `test_config_builder.py`: Configuration builder tests

### Shared Fixtures (tests/conftest.py)

- `temp_session`: Temporary session directory
- `api_key`: Together.ai API key (skips test if unavailable)
- `sample_config`: Pre-configured test config
- `config_file`: Temporary config.json file

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_poetry_agent.py

# Run tests matching pattern
pytest -k "test_name"

# Run with coverage
pytest --cov=. --cov-report=html

# Test specific component
pytest tests/test_config_builder.py -v
```

### Integration Testing

```bash
# Create config with Python API
python3 -c "
from config_builder import ConfigBuilder
from datetime import datetime
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
builder = ConfigBuilder()
builder.with_sports(['basketball', 'soccer', 'tennis'])
builder.save(f'output/configs/config_{timestamp}.json')
print(f'output/configs/config_{timestamp}.json')
"

# Run orchestrator
python3 orchestrator.py --config output/configs/config_TIMESTAMP.json

# Verify output
ls output/latest/
```

## Customization

### Add More Sports

Just tell Claude or use the ConfigBuilder API:

```python
from config_builder import ConfigBuilder
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ConfigBuilder() \
    .with_sports(['basketball', 'soccer', 'tennis', 'swimming', 'volleyball']) \
    .save(f'output/configs/config_{timestamp}.json')
```

### Disable Retries

**Option 1: In configuration**
```python
from config_builder import ConfigBuilder
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ConfigBuilder() \
    .with_sports(['basketball', 'soccer', 'tennis']) \
    .with_retry(False) \
    .save(f'output/configs/config_{timestamp}.json')
```

**Option 2: Modify orchestrator.py**
```python
orchestrator = SportsPoetryOrchestrator(retry_enabled=False)
```

### Add More Poetry Forms

1. Update `poetry_agent.py` to generate limerick, villanelle, etc.
2. Update `analyzer_agent.py` to analyze new forms
3. Update `metadata.json` structure to track new forms
4. Update tests to validate new forms

Example addition to `poetry_agent.py`:

```python
def generate_limerick(self, sport: str) -> str:
    """Generate a 5-line limerick about the sport."""
    # Implementation here
    pass

def run(self):
    # Existing haiku and sonnet generation
    self.generate_haiku(self.sport)
    self.generate_sonnet(self.sport)

    # Add limerick generation
    self.generate_limerick(self.sport)
```

### Switch Generation Modes

Create a new config with desired mode using ConfigBuilder:

**Template mode (fast, deterministic):**
```python
from config_builder import ConfigBuilder
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ConfigBuilder() \
    .with_sports(['basketball', 'soccer', 'tennis']) \
    .with_generation_mode('template') \
    .save(f'output/configs/config_{timestamp}.json')
```

**LLM mode (creative, unique):**
```python
from config_builder import ConfigBuilder
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ConfigBuilder() \
    .with_sports(['basketball', 'soccer', 'tennis']) \
    .with_generation_mode('llm') \
    .with_llm_provider('together') \
    .save(f'output/configs/config_{timestamp}.json')
```

### Modify Agent Timeout

Edit `orchestrator.py` at line 156 to change the timeout value:

```python
# Current default
timeout_seconds = 120

# Change to 5 minutes for slower LLM calls
timeout_seconds = 300
```

### Add Custom LLM Providers

1. Add new provider to `config_builder.py` validation
2. Implement provider-specific logic in `poetry_agent.py`
3. Update tests to cover new provider
4. Document API key requirements

## Advanced Usage

### Analyze Logs with jq

**Find all failures:**
```bash
cat output/latest/execution_log.jsonl | jq 'select(.action == "failed")'
```

**Average agent duration:**
```bash
cat output/latest/usage_log.jsonl | jq '.agent_results[].duration_s' | jq -s 'add/length'
```

**Most popular sports across all runs:**
```bash
cat output/*/usage_log.jsonl | jq -r '.sports[]' | sort | uniq -c | sort -rn
```

**View all session changelogs:**
```bash
find output -name "config.changelog.json" -exec cat {} \; | jq -s .
```

**Track performance trends:**
```bash
cat output/*/usage_log.jsonl | jq '{session: .session_id, duration: .total_duration_s, success_rate: (.agents_succeeded / .agents_launched)}'
```

### Run Multiple Times for Analysis

Each run creates a separate session directory, so you can run multiple times and analyze trends:

```bash
# Run 3 times with different sports
python3 orchestrator.py --config output/configs/config_20251103_120000.json
python3 orchestrator.py --config output/configs/config_20251103_120100.json
python3 orchestrator.py --config output/configs/config_20251103_120200.json

# Analyze average duration across all sessions
cat output/*/usage_log.jsonl | jq -s '.[].total_duration_s' | jq -s 'add/length'

# Compare success rates
cat output/*/usage_log.jsonl | jq '{session: .session_id, success_rate: (.agents_succeeded / .agents_launched * 100)}'
```

### Batch Processing with Python

```python
from config_builder import ConfigBuilder
from datetime import datetime
import subprocess
import time

# Define multiple sport sets
sport_sets = [
    ['basketball', 'soccer', 'tennis'],
    ['hockey', 'volleyball', 'swimming'],
    ['baseball', 'football', 'golf', 'rugby', 'cricket']
]

# Generate configs and run orchestrator for each
for sports in sport_sets:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_path = f'output/configs/config_{timestamp}.json'

    ConfigBuilder() \
        .with_sports(sports) \
        .with_generation_mode('template') \
        .save(config_path)

    subprocess.run(['python3', 'orchestrator.py', '--config', config_path])
    time.sleep(1)  # Brief pause between runs

print("Batch processing complete!")
```

### Continuous Integration Example

```yaml
# .github/workflows/test.yml
name: Test Sports Poetry Workflow

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest -v --cov=. --cov-report=xml

      - name: Integration test
        run: |
          python3 -c "
          from config_builder import ConfigBuilder
          from datetime import datetime
          timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
          ConfigBuilder() \
              .with_sports(['basketball', 'soccer', 'tennis']) \
              .save(f'output/configs/config_{timestamp}.json')
          "
          python3 orchestrator.py --config output/configs/config_*.json

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Learning Points

This demo demonstrates key patterns for building agentic workflows:

1. **Conversational Input** - Natural language → structured config
2. **Parallel Execution** - Multiple agents working simultaneously
3. **Provenance Logging** - Every action tracked with timestamps
4. **Graceful Degradation** - Failures don't stop the workflow
5. **Result Synthesis** - Final agent aggregates all outputs
6. **Auditability** - Can prove exactly what happened when
7. **Iterative Improvement** - Logs enable data-driven enhancement
8. **Session Isolation** - Each run is independent and reproducible
9. **Configuration Management** - Timestamped configs with changelog tracking
10. **Testing Strategy** - Unit tests for components, integration tests for workflow

## Next Steps

Potential enhancements and extensions:

### Features
- Add web UI for real-time monitoring
- Implement more poetry forms (limerick, villanelle, free verse)
- Add human feedback collection mechanism
- Support custom poetry templates
- Enable poem editing/refinement loops

### Infrastructure
- Create dashboards from usage logs (Grafana, etc.)
- Add Prometheus metrics export
- Implement distributed agent execution (Celery, Ray)
- Add result caching layer
- Support streaming output for long-running agents

### Analysis
- A/B test different prompting strategies
- Track quality metrics over time
- Implement automatic poem quality scoring
- Generate comparison reports across multiple runs
- Build recommendation system for optimal configurations

### Integration
- REST API for programmatic access
- Webhook support for event notifications
- Integration with external LLM providers
- Support for custom evaluation functions
- Plugin system for extensibility

## Documentation

- **[README.md](README.md)** - User-facing quick start guide
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Complete configuration reference
- **[CLAUDE.md](CLAUDE.md)** - Claude Code guidance for this repository
- **[.claude/skills/create_config/](/.claude/skills/create_config/)** - Interactive config skill
- Source code comments - Implementation details

## Contributing

When contributing to this project:

1. **Follow the architecture** - Respect the four-layer design
2. **Add tests** - All new features need unit and integration tests
3. **Update logs** - Add appropriate logging events
4. **Document changes** - Update relevant .md files
5. **Maintain backward compatibility** - Don't break existing configs
6. **Use ConfigBuilder** - For any config-related changes
7. **Run full test suite** - Ensure `pytest -v` passes

## Troubleshooting

### Common Development Issues

**Problem**: `ModuleNotFoundError` when importing custom modules
- **Solution**: Ensure you're running from the project root directory

**Problem**: Tests fail with "fixture not found"
- **Solution**: Check that `conftest.py` is in the `tests/` directory

**Problem**: Agent timeout during development
- **Solution**: Increase timeout in `orchestrator.py` line 156 or temporarily disable timeout

**Problem**: Logs not appearing in session directory
- **Solution**: Check log file migration logic in `orchestrator.py` lines 515-523

**Problem**: ConfigBuilder validation errors
- **Solution**: Review [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for validation rules

**Problem**: Parallel agents not running in parallel
- **Solution**: Check ThreadPoolExecutor configuration in `orchestrator.py` line 267

## License

MIT - Use this as a template for your own multi-agent workflows!

---

**Built with Claude Code** - Demonstrating agentic AI workflows
