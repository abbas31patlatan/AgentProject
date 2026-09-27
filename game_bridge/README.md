# Game Agent Bridge

Game Agent Bridge is a reusable bridge between isolated game-playing agents, GitHub Actions, and desktop games.

It has three independent layers:

1. **Network bridge**: GitHub-hosted workers fetch public HTTP/HTTPS resources, cache them, return small text results inline, and expose large results as workflow artifacts.
2. **Game profiles**: each game describes how to launch, observe, control, save, recover, and play it.
3. **Multi-agent coordination (GACP)**: many separate ChatGPT/agent sessions get unique identities, action ledgers, chat/mailboxes, task handoffs, presence, and exclusive leases for shared resources.

Read repository-root `AGENTS.md` before using the project from an AI-agent session.

## Network flow

Each agent creates an immutable request:

`game_bridge/requests/inbox/<agent-id>/<request-id>.json`

The worker writes:

`game_bridge/responses/agents/<agent-id>/<request-id>.json`

Small text responses up to 64 KiB are embedded directly, so an agent usually needs only one GitHub file read. Large payloads are included in the workflow artifact named `game-agent-bridge-output-<run id>`.

Requests are agent-scoped rather than stored in one shared queue, so concurrent GPT sessions do not overwrite one another.

The bridge accepts only public HTTP/HTTPS destinations. Loopback, private, link-local and otherwise non-global addresses are rejected. Custom authentication headers are not accepted.

## Multi-agent flow

Runtime coordination lives on the `agent-hub` branch.

Typical session:

`read protocol -> register unique ID -> heartbeat -> acquire lease if needed -> work -> action log -> chat/handoff -> release lease -> idle/offline`

See `coordination/PROTOCOL.md`.

## Game flow

A game lives under `games/<game-id>/` and normally contains:

- `profile.json`: machine-readable runtime/control/save metadata.
- `PLAYBOOK.md`: instructions for actually playing the game.
- `adapter.py`: optional game-specific automation when generic mouse/keyboard/screenshot control is insufficient.

Use `games/_template` as the starting point for new games.

A play cycle is:

`observe -> understand state -> acquire game lease -> choose action -> execute -> observe -> persist -> log -> release/handoff`

For turn-based games, never end the turn until mandatory choices and active-unit/city decisions have been checked.

## Validate

    python game_bridge/validate_profiles.py
    python game_bridge/coordination/validate_runtime.py

## Adding a new game

See `games/README.md`. A useful playbook documents both game strategy and operating procedure: launch, menus, observation, controls, save/recovery, safe pause points, irreversible actions, and how to verify that an action actually succeeded.
