# AgentProject multi-agent entrypoint

Any AI agent, ChatGPT session, automation worker, or coding agent using this repository MUST read this file first.

## Mandatory startup sequence

1. Read `game_bridge/coordination/PROTOCOL.md`.
2. Read `game_bridge/coordination/config.json`.
3. Use the coordination branch named in that config (currently `agent-hub`) for runtime coordination.
4. Create a unique agent ID for this chat/session. Never reuse another live agent's ID.
5. Register only under `game_bridge/coordination/runtime/agents/<agent-id>/`.
6. Update your own presence before substantial work.
7. Log meaningful actions under your own append-only action directory.
8. Use chat rooms or direct mailboxes for agent-to-agent communication.
9. Acquire a lease before mutating a shared/exclusive resource such as a game turn, shared save, task marked exclusive, or shared bridge control file.
10. Use a separate work branch for code changes: `agent/<agent-id>/<topic>`.

## Identity

Recommended ID form:

`gpt-<model-slug>-YYYYMMDD-<6-to-10-random-hex>`

Example:

`gpt-sol-20260928-a7f3c2`

Human-readable display names are optional; the immutable machine ID is authoritative.

## Never do this

- Do not write actions under another agent ID.
- Do not mutate another agent's profile.
- Do not overwrite an immutable message/action/task event.
- Do not assume a stale presence means a lock is free; inspect the lease itself.
- Do not put secrets, auth tokens, private conversation text, or sensitive user data in coordination files. This repository is public.
- Do not use a shared mutable JSON array as a message queue.

Runtime coordination is an event log, not a shared scratchpad. Unique files make concurrent writers cheap and conflict-resistant.

See `game_bridge/coordination/PROTOCOL.md` for the complete protocol.
