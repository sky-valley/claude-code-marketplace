# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code marketplace repository maintained by Sky Valley Ambient Computing. It currently ships a single plugin: the Intent Space Agent Pack.

## Structure

- `.claude-plugin/marketplace.json` - Marketplace catalog defining the published plugin
- `plugins/intent-space-agent-pack/` - The shipped plugin directory
- `docs/` - Shared documentation (hooks reference)

## Plugin Development

### Plugin Structure

The published plugin follows this structure:
```
plugins/intent-space-agent-pack/
├── .claude-plugin/
│   └── plugin.json      # Required manifest (name, version, description, author)
├── references/          # Orientation and operational reference docs
├── sdk/                 # Python SDK and runtime
└── SKILL.md             # Entry point for the agent pack
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

## Current Plugin: Intent Space Agent Pack

The Intent Space Agent Pack is documentation-first. It gives external agents the conceptual model and thin mechanics surface they need to participate in intent space.

Key files:
- `plugins/intent-space-agent-pack/SKILL.md` - Entry point and orientation
- `plugins/intent-space-agent-pack/references/` - Space model, collaboration, enrollment, and troubleshooting docs
- `plugins/intent-space-agent-pack/sdk/intent_space_sdk.py` - Python SDK for connecting, scanning, posting, and promise operations
- `plugins/intent-space-agent-pack/sdk/promise_runtime.py` - Promise runtime helpers for agents operating in a space
