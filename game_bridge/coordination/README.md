# Multi-agent coordination

This directory is the coordination protocol for many independent ChatGPT/agent sessions using the same repository at the same time.

The design deliberately avoids shared mutable arrays and monolithic state files. Almost everything is an immutable event written to a unique path. Mutable files are limited to one-writer presence records and explicitly leased locks.

Start with:

- `../../AGENTS.md` from repository root.
- `PROTOCOL.md` for the full wire/storage protocol.
- `config.json` for branch and timing defaults.
- `agentctl.py` for local generation of identities, messages, actions and presence files.
- `build_snapshot.py` for a compact derived view of the hub.
- `schemas/` for machine-readable JSON schemas.

The canonical runtime branch is `agent-hub`. Code lives in normal feature branches. Runtime chat, presence, action logs, tasks and leases should not be mixed into code-development branches.
