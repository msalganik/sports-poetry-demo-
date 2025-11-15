# Sports Poetry Multi-Agent Workflow Demo

A demonstration of Claude Code's multi-agent coordination capabilities, with full auditability and provenance tracking.

## Overview

This demo showcases how to build agentic workflows with:
- **Conversational input collection** - Natural dialogue with Claude
- **Parallel agent execution** - Multiple agents working simultaneously
- **Graceful error handling** - Continues despite failures
- **Comprehensive logging** - Full provenance and analytics
- **Result synthesis** - Final agent analyzes all outputs

## What It Does

1. **You tell Claude** which 3-5 sports you want poems about
2. **Claude validates** and writes timestamped config file
3. **Orchestrator launches** parallel poetry agents (one per sport)
4. **Each agent generates** a haiku and sonnet about their sport
5. **Analyzer agent** compares all poems and creates a report
6. **Logs capture** everything for auditability and improvement

## Quick Start

### Step 1: Create Configuration

The easiest way to get started is to chat with Claude Code:

```
You: Let's run the demo! I want poems about basketball, soccer, and tennis.

Claude: Great! I'll create the config file...
       [Uses create_config skill to collect all parameters]
       ✓ Created output/configs/config_20251103_184500.json
```

The Claude skill will:
- Ask for 3-5 sports (or interpret categories like "winter sports")
- Choose generation mode (template or LLM)
- Configure LLM settings if needed
- Validate API keys
- Auto-generate session ID and timestamp

**Alternative**: You can also use the Python API directly. See [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for details.

### Step 2: Run the Orchestrator

```bash
cd sports_poetry_demo
python3 orchestrator.py --config output/configs/config_20251103_184500.json
```

Watch the output as agents work in parallel:

```
[orchestrator] Reading configuration file
[orchestrator] Loaded config: 3 sports
[orchestrator] Launching 3 agents in parallel
[orchestrator] Launching poetry agent for basketball (attempt 1)
[orchestrator] Launching poetry agent for soccer (attempt 1)
[orchestrator] Launching poetry agent for tennis (attempt 1)
Agent basketball: Starting poetry generation
Agent soccer: Starting poetry generation
Agent tennis: Starting poetry generation
Agent basketball: Wrote haiku (3 lines)
Agent soccer: Wrote haiku (3 lines)
Agent tennis: Wrote haiku (3 lines)
Agent basketball: Wrote sonnet (14 lines)
Agent soccer: Wrote sonnet (14 lines)
Agent tennis: Wrote sonnet (14 lines)
Agent basketball: Complete
Agent soccer: Complete
Agent tennis: Complete
[orchestrator] All agents complete: 3 succeeded, 0 failed
[orchestrator] Launching analyzer agent
Analyzer: Starting analysis
Analyzer: Found 3 sports to analyze
Analyzer: Wrote analysis report
Analyzer: Complete
[analyzer] Analysis complete in 0.2s
[orchestrator] Usage log written. Total workflow time: 8.4s
[orchestrator] Workflow completed successfully
```

### Step 3: View Results

Check the `output/` directory:

```
output/latest/
├── basketball/
│   ├── haiku.txt          # 3-line haiku about basketball
│   ├── sonnet.txt         # 14-line sonnet about basketball
│   └── metadata.json      # Line counts, word counts, timestamps
├── soccer/
│   ├── haiku.txt
│   ├── sonnet.txt
│   └── metadata.json
├── tennis/
│   ├── haiku.txt
│   ├── sonnet.txt
│   └── metadata.json
└── analysis_report.md     # Comparative analysis of all poems
```

Read the analysis report:

```bash
cat output/latest/analysis_report.md
```

### Step 4: Review Logs (Optional)

**Detailed provenance** (every action):
```bash
cat output/latest/execution_log.jsonl | jq .
```

**Usage analytics** (aggregate stats):
```bash
cat output/latest/usage_log.jsonl | jq .
```

## How It Works

The demo uses a simple workflow:

```
User & Claude
     ↓
Creates config file
     ↓
Orchestrator (Python)
     ↓
Launches parallel agents
     ↓
Poetry Agents (one per sport)
     ↓
Wait for all to complete
     ↓
Analyzer Agent (synthesis)
     ↓
Output: poems + analysis + logs
```

**Key Features:**
- **Parallel execution**: All poetry agents run simultaneously
- **Session isolation**: Each run gets its own directory
- **Self-contained**: Sessions include config, outputs, and logs
- **Symlink**: `output/latest` always points to most recent session


## Troubleshooting

**Problem**: `ModuleNotFoundError`
- **Solution**: Ensure you're using Python 3.7+ (all modules are in stdlib except LLM dependencies)

**Problem**: Agents timeout
- **Solution**: LLM mode may take longer. Check `output/latest/execution_log.jsonl` for details.

**Problem**: No poems generated
- **Solution**: Check `output/latest/execution_log.jsonl` for error details

**Problem**: LLM mode fails
- **Solution**:
  - Verify API key is set: `echo $TOGETHER_API_KEY`
  - Install requirements: `pip install -r requirements.txt`
  - Check execution log for specific error

**Problem**: Analysis report is empty
- **Solution**: Ensure at least one agent succeeded. Check `output/latest/execution_log.jsonl` for failures.

## Documentation

- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Complete configuration reference and Python API docs
- **[DEVELOPER.md](DEVELOPER.md)** - Developer guide for customization and extension
- **[CLAUDE.md](CLAUDE.md)** - Claude Code guidance for this repository


## License

MIT - Use this as a template for your own multi-agent workflows!

---

**Built with Claude Code** - Demonstrating agentic AI workflows
