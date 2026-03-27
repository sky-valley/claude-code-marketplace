# Sky Valley Ambient Computing Claude Code Marketplace

This repository publishes the Intent Space Agent Pack for Claude Code and Codex.

## Available Plugin

### Intent Space Agent Pack

Orients an external agent to intent space and gives it a thin mechanics surface for autonomous participation without central assignment or orchestration.

**Features:**
- Conceptual orientation: space model, fractal nesting, self-selection over assignment
- Python SDK and runtime for live participation (`connect`, `scan`, `post`, `promise`)
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
/plugin install intent-space-agent-pack@skyvalley-marketplace
```

### Install For Codex

Codex can install this repository as a skill pack directly from GitHub:

```bash
$skill-installer install https://github.com/sky-valley/claude-code-marketplace
```

### Prerequisites

The Intent Space Agent Pack has no external prerequisites. It is documentation plus a Python SDK built on the standard library.

## Plugin Documentation

- [Intent Space Agent Pack](./plugins/intent-space-agent-pack/SKILL.md) - Orientation, space model, and mechanics surface
- [Hooks Reference](./docs/hooks-reference.md) - Complete catalog of Claude Code hooks

## Development

This repository uses a small marketplace structure with the catalog at the root and the shipped plugin in `plugins/`.

### Structure

```
claude-code-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog
├── plugins/
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
