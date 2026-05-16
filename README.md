# Agent Plugins

A curated marketplace of plugins for AI agents, forked from [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins).

## Overview

This repository contains a collection of plugins designed to extend the capabilities of AI agents. Plugins are organized into two primary marketplaces:

- **`.agents/plugins/marketplace.json`** — Core agent plugin registry
- **`.claude-plugin/marketplace.json`** — Claude-specific plugin registry

## Getting Started

### Prerequisites

- Node.js >= 18.x or Python >= 3.10
- An AI agent runtime that supports the plugin marketplace format

### Installation

Clone the repository:

```bash
git clone https://github.com/your-org/agent-plugins.git
cd agent-plugins
```

### Using a Plugin

Plugins are defined in the marketplace JSON files. Reference a plugin by its `id` in your agent configuration:

```json
{
  "plugins": [
    {
      "id": "plugin-id-here",
      "version": "1.0.0"
    }
  ]
}
```

## Plugin Marketplace Structure

Each marketplace entry follows this schema:

```json
{
  "id": "unique-plugin-id",
  "name": "Human Readable Name",
  "description": "What this plugin does",
  "version": "1.0.0",
  "author": "author-name",
  "tags": ["category", "use-case"],
  "entrypoint": "path/to/plugin",
  "permissions": []
}
```

## Contributing

We welcome contributions! Please read our contribution guidelines before submitting a pull request.

### Adding a New Plugin

1. Fork this repository
2. Add your plugin entry to the appropriate `marketplace.json`
3. Ensure your plugin follows the schema above
4. Submit a pull request with a clear description

### Reporting Issues

Use the GitHub Issue templates provided in `.github/ISSUE_TEMPLATE/` to report bugs, request features, or propose RFCs.

## Code Owners

See [CODEOWNERS](.github/CODEOWNERS) for maintainer information.

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This project is a fork of [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins). Thank you to the original authors and contributors.

---

> **Personal fork notes:** I'm using this primarily to experiment with the Claude-specific plugins. The `.agents/plugins/marketplace.json` registry is largely untouched; most of my local additions live in `.claude-plugin/marketplace.json`.
>
> My plugins-in-progress that aren't ready for upstream:
> - `claude-web-summarizer` — summarizes pages using Claude before passing to agent context
> - `claude-diff-reviewer` — reviews git diffs and leaves inline comments
> - `claude-note-taker` — captures key decisions and TODOs from a conversation into a local markdown file (early stages)
>
> **Syncing with upstream:** To pull in updates from the original repo, run:
> ```bash
> git remote add upstream https://github.com/awslabs/agent-plugins.git
> git fetch upstream
> git merge upstream/main
> ```
