# Claude Code Plugin Hooks: Complete Data Extraction Reference

**Based on official documentation from code.claude.com**

## Executive Summary

This document catalogs all hooks, data fields, and environment variables available to Claude Code plugins for maximum context extraction.

---

## Available Hook Events (10 Total)

| Hook Name | Trigger Point | Best For |
|-----------|--------------|----------|
| `PreToolUse` | Before Claude executes any tool | Intercepting/modifying tool parameters, validation |
| `PostToolUse` | After tool execution completes | Logging results, post-processing |
| `UserPromptSubmit` | When user submits a prompt (before Claude processes) | Enriching context, validation, preprocessing |
| `Notification` | When Claude Code sends notifications | Filtering alerts, custom notification handling |
| `Stop` | When main agent finishes responding | Session cleanup, summary logging |
| `SubagentStop` | When subagent (Task tool) finishes | Tracking sub-task completion |
| `PreCompact` | Before conversation history compression | Preserving important context before truncation |
| `SessionStart` | Session initialization or resume | Setup, environment configuration |
| `SessionEnd` | Session termination | Cleanup, final logging |
| `Notification` (typed) | Specific notification types (permissions, idle, etc.) | Fine-grained notification filtering |

---

## Hook Types & Execution Modes

### 1. Command Hooks (`type: "command"`)
- Execute bash scripts with full filesystem access
- Inherit Claude Code's working directory
- Default 60-second timeout (configurable)
- Receive JSON input via stdin
- Output control via exit codes and JSON stdout

### 2. Prompt Hooks (`type: "prompt"`)
- Query Claude Haiku LLM for context-aware decisions
- Best used with: `Stop`, `SubagentStop`, `UserPromptSubmit`, `PreToolUse`
- Natural language understanding for non-deterministic logic

---

## JSON Input Structure (stdin)

### Common Fields (All Hooks)

```json
{
  "session_id": "string",
  "transcript_path": "string",
  "cwd": "string",
  "permission_mode": "string",
  "hook_event_name": "string"
}
```

### Event-Specific Fields

#### PreToolUse / PostToolUse
```json
{
  "tool_name": "string",
  "tool_input": {
    "command": "string",              // Bash commands
    "description": "string",          // Human-readable description
    "file_path": "string",            // Edit/Write/Read file paths
    "content": "string",              // Write tool content
    "old_string": "string",           // Edit tool old text
    "new_string": "string",           // Edit tool new text
    "pattern": "string",              // Grep search pattern
    "path": "string",                 // Grep/Glob path
    "url": "string",                  // WebFetch URL
    "prompt": "string",               // WebFetch/Task prompts
    "subagent_type": "string",        // Task subagent type
    // ... (tool-specific parameters)
  },
  "tool_response": "string"           // PostToolUse only: execution result
}
```

#### UserPromptSubmit
```json
{
  "prompt": "string",                 // User's submitted text
  "stop_hook_active": boolean         // Whether Stop hook is active
}
```

#### Stop / SubagentStop
```json
{
  "reason": "string"                  // Completion reason/context
}
```

#### Notification
```json
{
  "notification_type": "string",      // Type of notification
  "message": "string"                 // Notification content
}
```

---

## Environment Variables

### Hook-Specific Variables

| Variable | Scope | Description |
|----------|-------|-------------|
| `$CLAUDE_PLUGIN_ROOT` | All hooks | Absolute path to plugin directory |
| `$CLAUDE_PROJECT_DIR` | All hooks | Absolute path to project root |
| `$CLAUDE_ENV_FILE` | SessionStart only | Path to file for persisting environment variables |
| `$CLAUDE_CODE_REMOTE` | All hooks | "true" for web execution, absent/false for local |

### Global Claude Code Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | API authentication for Claude models |
| `ANTHROPIC_MODEL` | Override default model selection |
| `DISABLE_TELEMETRY` | Opt out of Statsig analytics tracking |
| `MAX_THINKING_TOKENS` | Extended thinking budget for complex reasoning |
| `BASH_DEFAULT_TIMEOUT_MS` | Default timeout for Bash tool execution |
| `DISABLE_PROMPT_CACHING` | Disable prompt caching globally |
| `HTTP_PROXY` | HTTP proxy server for network requests |
| `HTTPS_PROXY` | HTTPS proxy server for network requests |

---

## Hook Output Control

### Exit Codes

| Exit Code | Behavior | Use Case |
|-----------|----------|----------|
| **0** | Success | Normal execution; stdout shown in transcript (except UserPromptSubmit/SessionStart where it adds context) |
| **2** | Blocking error | Stderr fed back to Claude for processing |
| **Other** | Non-blocking error | Stderr shown to user, execution continues |

### JSON Output Fields (stdout)

```json
{
  "continue": true/false,            // Whether Claude should continue
  "decision": "approve|block|allow|deny", // Permission decisions
  "updatedInput": {},                // Modify tool parameters (PreToolUse)
  "additionalContext": "string"      // Add context for Claude
}
```

---

## Tool Matching & Filtering

Hooks can target specific tools using matchers:

| Matcher Pattern | Matches |
|----------------|---------|
| `"Write"` | Exact tool name match |
| `"Edit\|Write"` | Regex: either Edit or Write |
| `"Notebook.*"` | Regex: all Notebook tools |
| `"*"` or `""` | All tools (wildcard) |
| `"mcp__memory__.*"` | MCP tools from specific server |

---

## Extractable Context & Data

### From tool_input (PreToolUse/PostToolUse)

#### Bash Tool
- `.tool_input.command` - Exact shell command
- `.tool_input.description` - What command does
- `.tool_input.timeout` - Execution timeout
- `.tool_input.run_in_background` - Background execution flag

#### Read Tool
- `.tool_input.file_path` - File being read
- `.tool_input.offset` - Line offset
- `.tool_input.limit` - Line limit

#### Edit Tool
- `.tool_input.file_path` - File being edited
- `.tool_input.old_string` - Text being replaced
- `.tool_input.new_string` - Replacement text
- `.tool_input.replace_all` - Replace all occurrences flag

#### Write Tool
- `.tool_input.file_path` - File being written
- `.tool_input.content` - Full file content

#### Grep Tool
- `.tool_input.pattern` - Search regex
- `.tool_input.path` - Search directory
- `.tool_input.glob` - File pattern filter
- `.tool_input.output_mode` - Output format
- `.tool_input.-i` - Case insensitive flag

#### Glob Tool
- `.tool_input.pattern` - File pattern
- `.tool_input.path` - Search directory

#### WebFetch Tool
- `.tool_input.url` - URL being fetched
- `.tool_input.prompt` - Query prompt for content

#### WebSearch Tool
- `.tool_input.query` - Search query
- `.tool_input.allowed_domains` - Domain whitelist
- `.tool_input.blocked_domains` - Domain blacklist

#### Task Tool (Subagents)
- `.tool_input.prompt` - Task instructions
- `.tool_input.subagent_type` - Agent type (Explore, Plan, etc.)
- `.tool_input.description` - Task summary
- `.tool_input.model` - Model to use (sonnet, opus, haiku)

#### TodoWrite Tool
- `.tool_input.todos` - Array of todo items with status

#### AskUserQuestion Tool
- `.tool_input.questions` - Questions being asked
- `.tool_input.answers` - User answers (if available)

### From Session Context
- `session_id` - Unique session identifier
- `transcript_path` - Path to conversation transcript file
- `cwd` - Current working directory
- `permission_mode` - Permission settings

### From Environment
- Project root directory path
- Plugin installation directory
- Remote vs local execution context
- User's shell environment and credentials

### From tool_response (PostToolUse)
- Complete tool execution output
- Command stdout/stderr
- File contents (Read tool)
- Search results (Grep/Glob)
- Web content (WebFetch/WebSearch)

---

## Execution Characteristics

### Timing & Parallelization
- **Parallelization**: All matching hooks run simultaneously
- **Deduplication**: Identical commands execute only once
- **Default timeout**: 60 seconds (configurable)

### Access & Permissions
- Hooks inherit user's credentials and permissions
- Full filesystem access via bash execution
- Access to system commands and installed tools
- Can read/write project files and transcript

### Working Directory
- Hooks execute in Claude Code's current working directory
- Can change directory within hook script
- `$CLAUDE_PROJECT_DIR` available for project-relative paths

---

## Maximum Context Extraction Strategy

To capture maximum detail, a plugin should:

1. **Hook into all 10 events** for complete lifecycle coverage
2. **Use wildcard matchers** (`"*"`) to capture all tools
3. **Log all JSON input fields** to persistent storage
4. **Capture environment variables** at each hook execution
5. **Read transcript file** (from `transcript_path`) for full conversation history
6. **Store tool_input and tool_response pairs** for complete audit trail
7. **Track session lifecycle** via SessionStart/SessionEnd with timestamps
8. **Monitor file system changes** by logging all Edit/Write operations
9. **Capture user intent** from UserPromptSubmit prompts
10. **Record Claude's reasoning** from Stop/SubagentStop events

### Sample Data Collection Script Structure

```bash
#!/bin/bash

# Read JSON input
INPUT=$(cat)

# Extract and log all fields
LOG_FILE="$CLAUDE_PROJECT_DIR/.claude-plugin-data/$(date +%Y%m%d-%H%M%S)-$RANDOM.json"
mkdir -p "$(dirname "$LOG_FILE")"

# Create comprehensive log entry
jq -n \
  --argjson input "$INPUT" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg plugin_root "$CLAUDE_PLUGIN_ROOT" \
  --arg project_dir "$CLAUDE_PROJECT_DIR" \
  --arg remote "$CLAUDE_CODE_REMOTE" \
  --arg pwd "$PWD" \
  '{
    timestamp: $timestamp,
    hook_data: $input,
    environment: {
      plugin_root: $plugin_root,
      project_dir: $project_dir,
      remote: $remote,
      pwd: $pwd
    }
  }' > "$LOG_FILE"

# Exit successfully
exit 0
```

### Enhanced Context Collection Script

For maximum data extraction, use this enhanced script:

```bash
#!/bin/bash

# Read JSON input from hook
INPUT=$(cat)

# Extract hook event name for conditional logic
HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // "unknown"')

# Create timestamped log directory
LOG_DIR="$CLAUDE_PROJECT_DIR/.claude-plugin-data/$(date +%Y-%m)"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%Y%m%d-%H%M%S)-$RANDOM-$HOOK_EVENT.json"

# Collect all environment variables
collect_env() {
  jq -n \
    --arg plugin_root "$CLAUDE_PLUGIN_ROOT" \
    --arg project_dir "$CLAUDE_PROJECT_DIR" \
    --arg env_file "$CLAUDE_ENV_FILE" \
    --arg remote "$CLAUDE_CODE_REMOTE" \
    --arg api_key_set "$([ -n "$ANTHROPIC_API_KEY" ] && echo "true" || echo "false")" \
    --arg model "$ANTHROPIC_MODEL" \
    --arg disable_telemetry "$DISABLE_TELEMETRY" \
    --arg max_thinking "$MAX_THINKING_TOKENS" \
    --arg bash_timeout "$BASH_DEFAULT_TIMEOUT_MS" \
    --arg http_proxy "$HTTP_PROXY" \
    --arg https_proxy "$HTTPS_PROXY" \
    --arg pwd "$PWD" \
    --arg user "$USER" \
    --arg home "$HOME" \
    '{
      plugin_root: $plugin_root,
      project_dir: $project_dir,
      env_file: $env_file,
      remote: $remote,
      api_key_set: $api_key_set,
      model: $model,
      disable_telemetry: $disable_telemetry,
      max_thinking: $max_thinking,
      bash_timeout: $bash_timeout,
      http_proxy: $http_proxy,
      https_proxy: $https_proxy,
      pwd: $pwd,
      user: $user,
      home: $home
    }'
}

# Read additional context files on SessionStart
read_context_files() {
  local context_data="{}"

  # Read settings files (if readable)
  for settings_file in \
    "/Library/Application Support/ClaudeCode/managed-settings.json" \
    "$CLAUDE_PROJECT_DIR/.claude/settings.local.json" \
    "$CLAUDE_PROJECT_DIR/.claude/settings.json" \
    "$HOME/.claude/settings.json"; do
    if [ -r "$settings_file" ]; then
      context_data=$(echo "$context_data" | jq \
        --arg file "$settings_file" \
        --slurpfile content "$settings_file" \
        '.settings += [{file: $file, content: $content[0]}]')
    fi
  done

  # Read memory files (if readable)
  for memory_file in \
    "/Library/Application Support/ClaudeCode/CLAUDE.md" \
    "$CLAUDE_PROJECT_DIR/CLAUDE.md" \
    "$CLAUDE_PROJECT_DIR/.claude/CLAUDE.md" \
    "$HOME/.claude/CLAUDE.md" \
    "$CLAUDE_PROJECT_DIR/CLAUDE.local.md"; do
    if [ -r "$memory_file" ]; then
      content=$(cat "$memory_file" | jq -Rs .)
      context_data=$(echo "$context_data" | jq \
        --arg file "$memory_file" \
        --argjson content "$content" \
        '.memory += [{file: $file, content: $content}]')
    fi
  done

  echo "$context_data"
}

# Extract transcript excerpt on Stop/SubagentStop
read_transcript_tail() {
  local transcript_path=$(echo "$INPUT" | jq -r '.transcript_path // ""')
  if [ -r "$transcript_path" ]; then
    # Get last 10 lines of transcript
    tail -n 10 "$transcript_path" | jq -Rs 'split("\n") | map(select(length > 0) | fromjson?)'
  else
    echo "[]"
  fi
}

# Collect system information
collect_system_info() {
  jq -n \
    --arg os "$(uname -s)" \
    --arg arch "$(uname -m)" \
    --arg hostname "$(hostname)" \
    --arg shell "$SHELL" \
    --arg git_user "$(git config user.name 2>/dev/null || echo 'unknown')" \
    --arg git_email "$(git config user.email 2>/dev/null || echo 'unknown')" \
    '{
      os: $os,
      arch: $arch,
      hostname: $hostname,
      shell: $shell,
      git_user: $git_user,
      git_email: $git_email
    }'
}

# Build comprehensive log entry
ENV_DATA=$(collect_env)
SYSTEM_INFO=$(collect_system_info)

# Conditional data based on hook type
EXTRA_DATA="{}"
if [ "$HOOK_EVENT" = "SessionStart" ]; then
  EXTRA_DATA=$(read_context_files)
elif [ "$HOOK_EVENT" = "Stop" ] || [ "$HOOK_EVENT" = "SubagentStop" ]; then
  TRANSCRIPT_TAIL=$(read_transcript_tail)
  EXTRA_DATA=$(jq -n --argjson tail "$TRANSCRIPT_TAIL" '{transcript_tail: $tail}')
fi

# Combine all data
jq -n \
  --argjson input "$INPUT" \
  --argjson env "$ENV_DATA" \
  --argjson system "$SYSTEM_INFO" \
  --argjson extra "$EXTRA_DATA" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg hook_version "1.0.0" \
  '{
    hook_version: $hook_version,
    timestamp: $timestamp,
    hook_data: $input,
    environment: $env,
    system: $system,
    additional_context: $extra
  }' > "$LOG_FILE"

# Optional: Index by session ID for easy lookup
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
SESSION_INDEX="$LOG_DIR/session-index.jsonl"
echo "{\"session_id\":\"$SESSION_ID\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"hook\":\"$HOOK_EVENT\",\"log_file\":\"$LOG_FILE\"}" >> "$SESSION_INDEX"

# Exit successfully
exit 0
```

### Data Storage Structure

Recommended storage organization:

```
$CLAUDE_PROJECT_DIR/.claude-plugin-data/
├── 2025-01/                           # Monthly directories
│   ├── 20250112-143022-12345-PreToolUse.json
│   ├── 20250112-143023-12346-PostToolUse.json
│   ├── 20250112-143025-12347-Stop.json
│   └── session-index.jsonl           # Fast session lookup
├── 2025-02/
└── metadata.json                      # Plugin metadata

# Session index format (one line per hook execution):
{"session_id":"abc123","timestamp":"2025-01-12T14:30:22Z","hook":"PreToolUse","log_file":"..."}
{"session_id":"abc123","timestamp":"2025-01-12T14:30:23Z","hook":"PostToolUse","log_file":"..."}
```

### Analysis & Querying

Query collected data using `jq`:

```bash
# Find all Write operations in a session
cat .claude-plugin-data/2025-01/session-index.jsonl | \
  jq -r 'select(.session_id=="abc123") | .log_file' | \
  xargs cat | \
  jq 'select(.hook_data.tool_name=="Write") | .hook_data.tool_input.file_path'

# Extract all user prompts
cat .claude-plugin-data/2025-01/*-UserPromptSubmit.json | \
  jq -r '.hook_data.prompt'

# Find most-used tools
cat .claude-plugin-data/2025-01/*-PreToolUse.json | \
  jq -r '.hook_data.tool_name' | sort | uniq -c | sort -rn

# Track file modifications over time
cat .claude-plugin-data/2025-01/*-PostToolUse.json | \
  jq -r 'select(.hook_data.tool_name=="Edit" or .hook_data.tool_name=="Write") |
    [.timestamp, .hook_data.tool_input.file_path] | @csv'
```

---

## Limitations & Constraints

### What's NOT Available
- Claude's internal reasoning state (outside of transcript)
- Model token usage or cost information
- Claude Code's internal configuration beyond exposed variables
- Direct access to Claude's knowledge cutoff or training data
- User's personal information beyond filesystem permissions

### Hook Constraints
- Cannot block SessionEnd termination (only cleanup/logging)
- 60-second default timeout may truncate long operations
- Prompt hooks only work well with specific events (Stop, SubagentStop, UserPromptSubmit, PreToolUse)
- Hooks cannot modify transcript history retroactively

---

## Plugin Configuration Example

### hooks/hooks.json - Maximum Coverage Setup

```json
{
  "PreToolUse": [
    {
      "name": "log-pre-tool",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh PreToolUse",
      "matcher": "*"
    }
  ],
  "PostToolUse": [
    {
      "name": "log-post-tool",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh PostToolUse",
      "matcher": "*"
    }
  ],
  "UserPromptSubmit": [
    {
      "name": "log-prompt",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh UserPromptSubmit"
    }
  ],
  "Notification": [
    {
      "name": "log-notification",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh Notification"
    }
  ],
  "Stop": [
    {
      "name": "log-stop",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh Stop"
    }
  ],
  "SubagentStop": [
    {
      "name": "log-subagent-stop",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh SubagentStop"
    }
  ],
  "PreCompact": [
    {
      "name": "log-pre-compact",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh PreCompact"
    }
  ],
  "SessionStart": [
    {
      "name": "log-session-start",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh SessionStart"
    }
  ],
  "SessionEnd": [
    {
      "name": "log-session-end",
      "command": "$CLAUDE_PLUGIN_ROOT/scripts/log-hook.sh SessionEnd"
    }
  ]
}
```

### .claude-plugin/plugin.json

```json
{
  "name": "context-collector",
  "version": "1.0.0",
  "description": "Maximum context extraction plugin for Claude Code",
  "author": "Your Name",
  "hooks": "./hooks/hooks.json"
}
```

---

## Configuration & Settings Hierarchy

### Settings File Locations (Precedence Order)

1. **Enterprise Policy** (highest priority)
   - macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
   - Linux/WSL: `/etc/claude-code/managed-settings.json`
   - Windows: `C:\ProgramData\ClaudeCode\managed-settings.json`

2. **Command-line arguments** (override settings files)

3. **Local project settings** (project-specific, not shared)
   - `.claude/settings.local.json`

4. **Shared project settings** (team-shared via git)
   - `.claude/settings.json`

5. **User settings** (lowest priority, personal defaults)
   - `~/.claude/settings.json`

### Key Settings Extractable Data

Settings files contain:
- `apiKeyHelper` - Custom script for auth header generation
- `model` - Model override configuration
- `permissions` - Allow/deny/ask rules for tools
- `env` - Environment variables for every session
- `cleanupPeriodDays` - Transcript retention period (default: 30 days)
- `companyAnnouncements` - Startup messages
- `includeCoAuthoredBy` - Commit attribution settings
- `forceLoginMethod` - Authentication restrictions
- `outputStyle` - System prompt behavior customization
- `statusLine` - Custom status line context
- `enabledPlugins` - Installed plugin list
- `extraKnownMarketplaces` - Additional plugin sources

**Hooks can read these files** for additional context about user preferences and organizational policies.

---

## Memory System & Context Files

### Memory File Hierarchy (All loaded automatically)

1. **Enterprise Memory** (organization-wide)
   - macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`
   - Linux: `/etc/claude-code/CLAUDE.md`
   - Windows: `C:\ProgramData\ClaudeCode\CLAUDE.md`

2. **Project Memory** (team-shared)
   - `./CLAUDE.md` or `./.claude/CLAUDE.md`

3. **User Memory** (personal across all projects)
   - `~/.claude/CLAUDE.md`

4. **Project Memory Local** (personal, project-specific)
   - `./CLAUDE.local.md`

### Extractable Context from Memory Files

Memory files store:
- **Code styling preferences** - Naming conventions, formatting rules
- **Architectural patterns** - Project structure, design principles
- **Frequently-used commands** - Common workflows, scripts
- **Security policies** - Compliance requirements, coding standards
- **Project documentation** - Setup instructions, guidelines

**File imports**: CLAUDE.md files support `@path/to/import` syntax (max 5 levels deep) for modular organization.

**Hook access**: Read memory files during SessionStart to understand user preferences and project context.

---

## Transcript & Session Storage

### Transcript Files

| File Pattern | Contains |
|-------------|----------|
| `transcript_path` | Main conversation in JSONL format |
| `agent-{agentId}.jsonl` | Subagent conversation transcripts |
| Session directory | All related conversation files |

### Transcript Structure (JSONL)

Each line contains a message object with:
- `role` - "user", "assistant", or "system"
- `content` - Message text or tool use blocks
- `timestamp` - Message creation time
- `tool_use` blocks - Tool invocations with parameters
- `tool_result` blocks - Tool execution results

**Extractable from transcripts:**
- Complete conversation history
- All tool invocations and results
- User prompts and Claude responses
- System messages and reminders
- Thinking processes (if enabled)
- Token usage per turn
- Error messages and corrections

### Session Metadata

Session IDs can be extracted from:
- `session_id` field in hook JSON input
- Transcript filename patterns
- `.claude/sessions/` directory structure

---

## CLI Flags & Headless Mode

### Available CLI Flags (Extractable Context)

| Flag | Data Extractable |
|------|-----------------|
| `--add-dir` | Additional working directories |
| `--agents` | Dynamically defined subagents (JSON) |
| `--allowedTools` | Pre-approved tools list |
| `--disallowedTools` | Blocked tools list |
| `--system-prompt` | Custom system prompt text |
| `--system-prompt-file` | System prompt file path |
| `--append-system-prompt` | Additional system instructions |
| `--output-format` | text, json, or stream-json |
| `--input-format` | text or stream-json |
| `--verbose` | Verbose logging enabled |
| `--max-turns` | Maximum agentic iterations |
| `--model` | Model selection |
| `--permission-mode` | Permission level |
| `--mcp-config` | MCP server configuration |

### Headless Output Formats

**JSON Output Structure:**
```json
{
  "result": "string",
  "metadata": {
    "cost": "number",
    "duration": "number",
    "turn_count": "number"
  },
  "session_id": "string",
  "error": "boolean"
}
```

**Stream-JSON (JSONL):** Individual messages as they arrive, enabling real-time monitoring.

---

## Subagent Context & Storage

### Subagent Configuration Files

**Locations:**
- Project-level: `.claude/agents/` (highest priority)
- User-level: `~/.claude/agents/`
- Plugin-based: Via plugin manifest

**File format:** Markdown with YAML frontmatter:
```yaml
---
name: agent-name
description: Agent purpose
tools: Read,Grep,Bash
model: sonnet
---
Instructions here...
```

### Subagent Execution Context

**Available to subagents:**
- Separate context window from main conversation
- Configurable tool subset
- Model selection (sonnet, opus, haiku, inherit)
- Task description and user request
- Main conversation context (optionally)

**Subagent transcript storage:**
- Format: `agent-{agentId}.jsonl`
- Location: Same directory as main transcript
- Contains: Complete subagent conversation history
- Resumable: Can continue previous subagent sessions

### SubagentStop Hook Data

SubagentStop hooks receive:
- `session_id` - Parent session
- `reason` - Completion reason
- Access to `agent-{agentId}.jsonl` transcript
- Subagent results returned to main thread

---

## Slash Commands & Custom Tools

### Slash Command Structure

**Storage locations:**
- Project: `.claude/commands/` (team-shared)
- Personal: `~/.claude/commands/` (user-specific)
- Plugin: Via plugin manifest
- MCP: Format `/mcp__<server>__<prompt>`

**Frontmatter fields:**
```yaml
---
allowed-tools: Read,Edit,Bash
argument-hint: <filename>
description: Command description
model: sonnet
disable-model-invocation: false
---
```

### Command Context Access

**Available in slash commands:**
- Current git status (`git status`, `git diff`)
- Recent commits history
- File contents via `@filename` syntax
- Bash execution via `!command` prefix
- Variables: `$ARGUMENTS`, `$1`, `$2`, etc.
- Extended thinking mode (via keywords)
- Tool restrictions (via `allowed-tools`)

### SlashCommand Tool Invocation

When Claude invokes SlashCommand tool:
- `.tool_input.command` - Command name and arguments
- `.tool_input.description` - What command does
- Hook captures invocation via PreToolUse/PostToolUse

---

## MCP Server Integration

### MCP Tool Pattern

MCP tools follow naming: `mcp__<server>__<tool>`

**Examples:**
- `mcp__memory__store` - Memory storage
- `mcp__github__create_issue` - GitHub issue creation
- `mcp__notion__query_database` - Notion database query

### MCP Configuration Files

**Locations:**
- Local: Project-specific, user-private (default)
- Project: `.mcp.json` (team-shared)
- User: Cross-project configuration

**Transport types:**
- HTTP servers (recommended for remote)
- Stdio servers (local processes)
- SSE servers (deprecated)

### MCP Extractable Data

**From hooks:**
- All MCP tool invocations (via matcher `"mcp__.*"`)
- Server-specific tools (via matcher `"mcp__memory__.*"`)
- Tool parameters and responses
- Authentication events (OAuth 2.0)
- Resource mentions (`@resource`)
- MCP prompt invocations (as slash commands)

**40+ available MCP servers across categories:**
- Development & Testing: Sentry, Socket, Jam, Hugging Face
- Project Management: Asana, Jira, Linear, Monday, Notion, ClickUp
- Data Management: Airtable, HubSpot, Daloopa
- Payments: Stripe, PayPal, Square, Plaid
- Design: Figma, Canva, Cloudinary, invideo
- Infrastructure: Vercel, Netlify, Stytch, Cloudflare
- Automation: Zapier, Workato

---

## Plugin System Architecture

### Plugin Directory Structure

```
plugin-root/
├── .claude-plugin/
│   └── plugin.json          # Required manifest
├── commands/                # Slash commands (Markdown)
├── agents/                  # Subagent definitions (Markdown)
├── skills/                  # Agent Skills (SKILL.md)
├── hooks/
│   └── hooks.json          # Hook configurations
└── .mcp.json               # MCP server definitions
```

### Plugin Manifest (plugin.json)

**Required:**
- `name` - Unique kebab-case identifier

**Optional metadata:**
- `version`, `description`, `author`
- `homepage`, `repository`, `license`, `keywords`

**Component references:**
- `commands` - File/directory paths (string or array)
- `agents` - Agent directories
- `hooks` - Configuration path or inline JSON
- `mcpServers` - Server definitions

### Skills System

**Structure:** Directory with `SKILL.md` file

**Frontmatter:**
```yaml
---
name: skill-name
description: Skill purpose (max 1024 chars)
allowed-tools: Read,Bash,Grep
---
```

**Invocation:** Model-invoked (Claude decides when to use)

**Storage locations:**
- Personal: `~/.claude/skills/`
- Project: `.claude/skills/` (git-shared)
- Plugin: Via plugin manifest

**Extractable context:**
- Skill invocations (implicit, no tool event)
- Supporting files (scripts, templates)
- Tool usage within skills (via PreToolUse/PostToolUse)

---

## Additional Notes

### Transcript Access
The `transcript_path` field provides path to the conversation transcript file. This can be read to access:
- Complete conversation history
- Claude's previous responses and reasoning
- User's prior prompts
- Tool execution results
- System messages and reminders

### MCP Tool Integration
Tools from MCP servers follow pattern: `mcp__<server>__<tool>`. Matchers can target:
- Specific MCP server: `"mcp__memory__.*"`
- All MCP tools: `"mcp__.*"`
- Individual MCP tool: `"mcp__memory__store"`

### Safe JSON Parsing in Bash

```bash
# Safe property access with defaults
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // "unknown"')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')

# Check if field exists
if echo "$INPUT" | jq -e '.tool_response' > /dev/null; then
  # Field exists
  RESPONSE=$(echo "$INPUT" | jq -r '.tool_response')
fi
```

---

## Summary: Complete Data Extraction Checklist

### Core Hook System
- ✅ **10 hook events** - All lifecycle stages covered
- ✅ **5 common JSON fields** - session_id, transcript_path, cwd, permission_mode, hook_event_name
- ✅ **12 environment variables** - Hook-specific (4) + Global Claude Code (8)
- ✅ **Tool-specific input parameters** - All 15+ tools with unique fields
- ✅ **Tool execution results** - PostToolUse tool_response
- ✅ **User prompts** - UserPromptSubmit prompt field
- ✅ **Completion context** - Stop/SubagentStop reason field
- ✅ **Notification data** - Notification type and message

### File System & Configuration
- ✅ **5 settings file locations** - Enterprise → User hierarchy
- ✅ **12+ settings fields** - Model, permissions, env, plugins, etc.
- ✅ **4 memory file locations** - Enterprise → Project hierarchy
- ✅ **Memory file imports** - @path syntax, 5 levels deep
- ✅ **Transcript files** - Main + subagent JSONL transcripts
- ✅ **Session directory structure** - .claude/sessions/ organization

### Transcripts & Sessions
- ✅ **JSONL message structure** - role, content, timestamp, tool blocks
- ✅ **Conversation history** - Complete user/assistant/system messages
- ✅ **Tool invocations** - Parameters, results, timing
- ✅ **Thinking processes** - Extended reasoning (if enabled)
- ✅ **Token usage** - Per-turn consumption data
- ✅ **Session metadata** - IDs, filenames, directory structure

### CLI & Headless Mode
- ✅ **15+ CLI flags** - Model, tools, permissions, output, etc.
- ✅ **3 output formats** - text, json, stream-json
- ✅ **JSON metadata** - cost, duration, turn_count
- ✅ **Resume capabilities** - --continue, --resume flags

### Subagents & Commands
- ✅ **Subagent configuration** - YAML frontmatter (name, description, tools, model)
- ✅ **Subagent transcripts** - agent-{agentId}.jsonl files
- ✅ **Subagent context** - Separate context window, tool subset
- ✅ **Slash command structure** - Frontmatter fields, parameters
- ✅ **Command context** - Git status, file contents, bash output
- ✅ **Command parameters** - $ARGUMENTS, $1, $2, @filename, !command

### MCP Integration
- ✅ **MCP tool pattern** - mcp__<server>__<tool> naming
- ✅ **40+ MCP servers** - 7 categories (dev, PM, data, payments, design, infra, automation)
- ✅ **3 transport types** - HTTP, stdio, SSE
- ✅ **Configuration locations** - Local, project, user
- ✅ **Resource mentions** - @resource syntax
- ✅ **OAuth authentication** - Auth event tracking

### Plugin System
- ✅ **Plugin directory structure** - .claude-plugin/, commands/, agents/, skills/, hooks/
- ✅ **Manifest fields** - name, version, author, homepage, components
- ✅ **Skills system** - SKILL.md with frontmatter, model-invoked
- ✅ **3 storage locations** - Personal, project, plugin

### Additional Context Sources
- ✅ **Project root** - CLAUDE_PROJECT_DIR path
- ✅ **Plugin root** - CLAUDE_PLUGIN_ROOT path
- ✅ **Current working directory** - cwd field
- ✅ **Remote vs local** - CLAUDE_CODE_REMOTE flag
- ✅ **User credentials** - Inherited from shell environment
- ✅ **Filesystem access** - Full read/write via bash
- ✅ **System commands** - All installed tools accessible
- ✅ **Timing data** - System timestamps at execution

**Total extractable data categories: 15+**
**Total extractable data points: 200+** (varies by tool, event type, and configuration)

### Data Capture Strategy for Maximum Context

A comprehensive plugin should:

1. **Hook all 10 events** with wildcard matchers (`"*"`)
2. **Log complete JSON input** from stdin for every hook
3. **Read transcript files** via `transcript_path` for conversation history
4. **Read subagent transcripts** (agent-*.jsonl) for sub-task details
5. **Read settings files** (all 5 locations) for user/org preferences
6. **Read memory files** (all 4 locations + imports) for context
7. **Capture environment variables** (all 12) at each execution
8. **Monitor file operations** (Read/Edit/Write tools) for change tracking
9. **Track MCP operations** (all mcp__* tools) for external integrations
10. **Record CLI context** (flags, output format) from process inspection
11. **Store session metadata** (IDs, paths, timestamps) for timeline reconstruction
12. **Parse command invocations** (slash commands, subagents) for workflow analysis

---

*Document generated from official Claude Code documentation at code.claude.com*
*Last updated: 2025-11-12*
