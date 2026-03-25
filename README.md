# Sky Valley Ambient Computing Claude Code Marketplace

A collection of Claude Code plugins developed by Sky Valley Ambient Computing.

## Available Plugins

### Differ

Captures Claude Code intent data (prompts, tool usage, session lifecycle) and sends it to [Differ.app](https://getdiffer.com) for correlation with file changes.

**Features:**
- Captures all hook events (tool usage, user prompts, session lifecycle)
- Non-blocking integration (never interrupts workflow)
- Automatic correlation with file system changes in Differ.app
- Zero external dependencies (Python 3 stdlib only)

**Version:** 2.1.1

### Intent Space Agent Pack

Orients an external agent to intent space and gives it a thin mechanics surface for autonomous participation — without central assignment or orchestration.

**Features:**
- Conceptual orientation: space model, fractal nesting, self-selection over assignment
- Python SDK and runtime for live participation (connect, scan, post, promise)
- Station enrollment mechanics (Welcome Mat, DPoP signup, tokens)
- Steward pattern for space provisioning through promises
- Emergent multi-agent collaboration patterns (coordination, contention, cascade, refinement, swarm decomposition)

**Version:** 1.0.0

## Installation

### Add the Marketplace

```bash
/plugin marketplace add https://github.com/sky-valley/claude-code-marketplace.git
```

### Install a Plugin

```bash
# Install the Differ plugin
/plugin install differ@skyvalley-marketplace

# Install the Intent Space Agent Pack
/plugin install intent-space-agent-pack@skyvalley-marketplace
```

### Install For Codex

Codex can install this repository as a skill pack directly from GitHub:

```bash
$skill-installer install https://github.com/sky-valley/claude-code-marketplace
```

### Prerequisites

**Differ** requires:
- [Differ.app](https://getdiffer.com) running on your system
- Python 3 (comes with macOS)
- `differ-cli` binary accessible (automatically detected)

**Intent Space Agent Pack** has no external prerequisites — it is documentation and a Python SDK (stdlib only).

## Plugin Documentation

- [Differ Plugin README](./plugins/differ/README.md) - Installation, usage, and troubleshooting
- [Intent Space Agent Pack](./plugins/intent-space-agent-pack/SKILL.md) - Orientation, space model, and mechanics surface
- [Hooks Reference](./docs/hooks-reference.md) - Complete catalog of Claude Code hooks

## Development

This repository uses a monorepo structure with the marketplace catalog at the root and plugins in the `plugins/` directory.

### Structure

```
claude-code-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog
├── plugins/
│   ├── differ/                   # Differ plugin
│   └── intent-space-agent-pack/  # Intent Space Agent Pack
├── docs/                         # Shared documentation
└── README.md
```

### Local Development

To test plugins locally before pushing:

```bash
# Add local marketplace
/plugin marketplace add /Users/noam/work/skyvalley/claude-code-marketplace

# Install a plugin from local marketplace
/plugin install {plugin-name}@skyvalley-marketplace
```

## License

MIT License - see individual plugin directories for details.

## Support

For issues or questions, open an issue on [GitHub](https://github.com/sky-valley/claude-code-marketplace/issues).
