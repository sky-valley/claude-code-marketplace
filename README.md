# Sky Valley Ambient Computing Claude Code Marketplace

A collection of Claude Code plugins developed by Sky Valley Ambient Computing.

## Available Plugins

### Differ

Captures Claude Code intent data (prompts, tool usage, session lifecycle) and sends it to [Differ.app](https://differ.app) for correlation with file changes.

**Features:**
- Captures all hook events (tool usage, user prompts, session lifecycle)
- Non-blocking integration (never interrupts workflow)
- Automatic correlation with file system changes in Differ.app
- Zero external dependencies (Python 3 stdlib only)

**Version:** 2.0.0

## Installation

### Add the Marketplace

```bash
/plugin marketplace add https://github.com/sky-valley/claude-code-marketplace.git
```

### Install the Differ Plugin

```bash
/plugin install differ@skyvalley-marketplace
```

### Prerequisites

The Differ plugin requires:
- [Differ.app](https://differ.app) running on your system
- Python 3 (comes with macOS)
- `differ-cli` binary accessible (automatically detected)

## Plugin Documentation

- [Differ Plugin README](./plugins/differ/README.md) - Installation, usage, and troubleshooting
- [Hooks Reference](./docs/hooks-reference.md) - Complete catalog of Claude Code hooks

## Development

This repository uses a monorepo structure with the marketplace catalog at the root and plugins in the `plugins/` directory.

### Structure

```
claude-code-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog
├── plugins/
│   └── differ/                   # Differ plugin
├── docs/                         # Shared documentation
└── README.md
```

### Local Development

To test plugins locally before pushing:

```bash
# Add local marketplace
/plugin marketplace add /Users/noam/work/skyvalley/claude-code-marketplace

# Install from local marketplace
/plugin install differ@skyvalley-marketplace
```

## License

MIT License - see individual plugin directories for details.

## Support

For issues or questions:
- Open an issue on [GitHub](https://github.com/sky-valley/claude-code-marketplace/issues)
- Email: founder@skyvalley.ac
