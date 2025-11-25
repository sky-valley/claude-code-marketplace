# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code plugin marketplace maintained by Sky Valley Ambient Computing. It hosts Claude Code plugins that can be installed via the plugin system.

## Structure

- `.claude-plugin/marketplace.json` - Marketplace catalog defining available plugins
- `plugins/` - Plugin directories (each is a self-contained Claude Code plugin)
- `docs/` - Shared documentation (hooks reference)

## Plugin Development

### Plugin Structure

Each plugin in `plugins/` follows this structure:
```
plugins/{name}/
├── .claude-plugin/
│   └── plugin.json      # Required manifest (name, version, description, author)
├── hooks/
│   └── hooks.json       # Hook configurations
├── scripts/             # Hook implementation scripts
├── commands/            # Slash commands (markdown files)
└── README.md
```

### Testing Locally

```bash
# Add local marketplace
/plugin marketplace add /path/to/claude-code-marketplace

# Install plugin from local marketplace
/plugin install {plugin-name}@skyvalley-marketplace

# Verify installation
/plugins
```

### Hooks System

The differ plugin demonstrates comprehensive hook usage:
- Hook events: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, SessionStart, SessionEnd, PreCompact, Notification
- Matcher `"*"` captures all tools
- Scripts receive JSON via stdin, control behavior via exit codes and stdout JSON

Hook scripts should be non-blocking (always return exit code 0) to avoid interrupting Claude Code workflows.

### Slash Commands

Commands are markdown files with YAML frontmatter:
```yaml
---
description: Command description
allowed-tools: Read, Bash(sqlite3:*), ...
argument-hint: [hint text]
---
```

The command body defines the prompt expansion with `$ARGUMENTS` for user input.

## Current Plugin: Differ

Captures Claude Code intent data (prompts, tool usage, session lifecycle) and sends to Differ.app for correlation with file changes.

Key files:
- `plugins/differ/scripts/send_to_differ.py` - Main capture script (Python 3, stdlib only)
- `plugins/differ/hooks/hooks.json` - Hook configuration
- `plugins/differ/commands/differ.md` - Query command for coding history

The script auto-detects differ-cli from `.differ-debug/` (debug) or `.differ/` (release) directories.
