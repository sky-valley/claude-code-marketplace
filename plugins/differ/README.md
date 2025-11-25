# Differ Claude Code Plugin

Capture Claude Code intent data and send to Differ.app for correlation with file changes.

## What This Plugin Does

This plugin automatically captures all Claude Code session activity and sends it to Differ.app:

- **User prompts** - Every prompt you submit to Claude
- **Tool usage** - All tool invocations (Edit, Write, Read, Bash, etc.) with parameters
- **Tool results** - Output from each tool execution
- **Session lifecycle** - Start, stop, and completion events
- **Conversation context** - Transcript paths, working directories, session IDs

Differ.app correlates this intent data with filesystem changes, allowing you to see **why** code changed, not just **what** changed.

## Prerequisites

- **Differ.app** must be installed and running
- **differ-cli** must be installed in your project (Differ.app does this automatically when you add a project)
- **Python 3** (pre-installed on macOS and most Linux distributions)

## Installation

### Via Local Marketplace (Development)

From a Claude Code session:

```bash
# Add the local marketplace
/plugin marketplace add /path/to/Differ/dev-marketplace

# Install the plugin
/plugin install differ@dev-marketplace
```

This method keeps the plugin in sync with your development repository since the marketplace references the actual plugin location.

### Verify Installation

After installation, verify the plugin is loaded:

```bash
# In any Claude Code session
/plugins
```

You should see "differ" in the list of installed plugins.

## Usage

### Query Your History with `/differ`

The plugin includes a slash command that lets you query your coding history using natural language:

```bash
/differ what sessions did I have today?
/differ what files did I change in my last session?
/differ show me the prompts that led to changes in Database.swift
/differ what tools were used yesterday?
/differ show me the previous version of AppCoordinator.swift
```

The command has full access to:
- **Session data** - When sessions started/ended, which branch
- **File changes** - What files were created/modified/deleted and when
- **User prompts** - Every prompt you submitted
- **Tool usage** - What tools Claude used and their results
- **File snapshots** - Previous versions of files (stored as blobs)
- **Transcripts** - Full conversation history

### Automatic Capture

Once installed, the plugin works automatically. No configuration needed.

Every time you:
- Submit a prompt to Claude
- Claude uses a tool (Edit, Write, Bash, etc.)
- A session starts or stops

...the plugin captures the data and sends it to Differ.app.

### Verify Capture

Check that events are being captured:

1. **Open Differ.app** and ensure your project is added
2. **Run a Claude Code session** in that project
3. **Check the database** (when UI is built, you'll see the timeline)

Or query directly:

```bash
# From your project directory
sqlite3 ~/Library/Application\ Support/Differ/differ.db \
  "SELECT COUNT(*) FROM hook_events WHERE session_id = 'YOUR_SESSION_ID';"
```

### Debug Mode

To see detailed hook execution logs:

```bash
claude --debug
```

This shows which hooks fired, what commands executed, and any errors.

## How It Works

### Architecture

```
Claude Code Session
       ↓
Hook Events (PreToolUse, PostToolUse, UserPromptSubmit, etc.)
       ↓
send-to-differ.sh script
       ↓
differ-cli send-event (via Unix socket)
       ↓
Differ.app SocketServer
       ↓
SQLite database (hook_events table)
```

### Hook Events Captured

The plugin registers the following hooks:

| Hook | When | Captures |
|------|------|----------|
| **PreToolUse** | Before tool execution | Tool name, parameters |
| **PostToolUse** | After tool execution | Tool name, parameters, result |
| **UserPromptSubmit** | User submits prompt | Prompt text |
| **Stop** | Main agent finishes | Completion reason |
| **SubagentStop** | Subagent finishes | Completion reason |
| **SessionStart** | Session begins | Session metadata |
| **SessionEnd** | Session ends | Session cleanup |
| **PreCompact** | Before context compression | Context state |

All hooks use a wildcard matcher `"*"` to capture every tool invocation.

### Data Format

Events are sent as JSON matching the `HookData` structure in `Differ/Integration/WireProtocol.swift`:

```json
{
  "version": "1.0.0",
  "session_id": "abc123...",
  "hook_event_name": "PostToolUse",
  "timestamp": 1700000000.123,
  "cwd": "/path/to/project",
  "transcript_path": "/path/to/transcript.jsonl",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "src/main.swift",
    "old_string": "...",
    "new_string": "..."
  },
  "tool_response": "File edited successfully"
}
```

## Troubleshooting

### Plugin Not Loading

**Check installation:**
```bash
ls -la ~/.claude/plugins/differ
```

You should see `.claude-plugin/`, `hooks/`, and `scripts/` directories.

**Reload plugins:**
```bash
# In Claude Code
/plugins
```

### Events Not Captured

**Check differ-cli exists:**

The plugin auto-detects Debug and Release builds:

```bash
# Debug build (prioritized during development)
ls -la .differ-debug/differ-cli

# Release build
ls -la .differ/differ-cli
```

If missing, open Differ.app and add your project. The app installs the CLI to:
- `.differ-debug/` for Debug builds (`ac.skyvalley.Differ.Debug`)
- `.differ/` for Release builds (`ac.skyvalley.Differ`)

**Check Differ.app is running:**
```bash
pgrep -l Differ
```

**Check socket server:**
```bash
ls -la ~/Library/Application\ Support/Differ/differ.sock
```

**Check failed events log:**
```bash
# Debug
cat .differ-debug/failed-events.jsonl

# Release
cat .differ/failed-events.jsonl
```

### Python Not Available

Python 3 is pre-installed on macOS and most Linux systems. If needed:

```bash
# macOS (via Homebrew)
brew install python3

# Ubuntu/Debian
sudo apt-get install python3
```

### Permission Errors

Ensure the script is executable:

```bash
chmod +x ~/.claude/plugins/differ/scripts/send_to_differ.py
```

## Development

### Testing the Script Manually

Create a test hook input:

```bash
echo '{
  "session_id": "test-session",
  "hook_event_name": "UserPromptSubmit",
  "cwd": "/tmp",
  "transcript_path": "/tmp/test.jsonl",
  "prompt": "Hello, Claude!"
}' | ./scripts/send_to_differ.py
```

### Debugging Hook Execution

1. **Add debug prints** to `send_to_differ.py` if needed (prints to stderr are visible)
2. **Run Claude Code with debug flag:** `claude --debug`
3. **Check stderr output** for hook execution details
4. **Review failed events:** `cat .differ/failed-events.jsonl`

### Modifying Hook Events

Edit `hooks/hooks.json` to:
- Add/remove hook events
- Change matchers (e.g., only capture `Edit|Write` tools)
- Add custom logic per hook type

After modifying, reload:

```bash
# In Claude Code
/hooks
```

## Architecture Notes

This plugin is designed to work with Differ 2.0's architecture:

- **Local-first**: All data stays on your machine
- **Non-blocking**: Hook failures don't interrupt your workflow
- **Automatic**: No manual intervention required
- **Comprehensive**: Captures all intent data for correlation

The correlation happens in Differ.app's EventCorrelator, which links:
- File events (from DirectoryWatcher) ↔ Claude sessions (from hooks)
- Exact matches: tool use with explicit file paths
- Temporal matches: events during session window
- Post-session matches: events shortly after session ends

## License

Same license as Differ.app (see repository LICENSE).

## Support

For issues or questions:
- Check Differ.app logs: `~/Library/Application Support/Differ/logs/`
- Query database: `sqlite3 ~/Library/Application Support/Differ/differ.db`
- Review socket server logs in Differ.app console

---

**Status**: This plugin is part of Differ 2.0 and is actively developed.
**Last Updated**: 2025-11-25
