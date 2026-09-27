# Game Agent Bridge

Game Agent Bridge is a reusable bridge between an isolated game-playing agent, GitHub Actions, and desktop games.

It has two independent layers:

1. Network bridge: a GitHub-hosted worker fetches public HTTP/HTTPS resources, caches them, returns small text results inline, and exposes large results as workflow artifacts.
2. Game profiles: every supported game describes how to launch, observe, control, save, recover, and play the game.

The design goal is that adding a second or tenth game should not require redesigning the agent.

## Network flow

Agent -> game_bridge/requests/queue.json -> GitHub Actions -> public Internet

The worker writes game_bridge/responses/latest.json. Text responses up to 64 KiB are embedded there, so an agent can usually read the response with one GitHub file read. Larger payloads are included in the workflow artifact named game-agent-bridge-output-<run id>.

The bridge intentionally accepts only public HTTP/HTTPS destinations. Loopback, private, link-local and otherwise non-global addresses are rejected. Custom authentication headers are not accepted by the queue format. This keeps the worker useful as a fetch/cache relay without turning it into a path to private runner services.

## Game flow

A game lives under game_bridge/games/<game-id>/ and normally contains:

- profile.json: machine-readable runtime/control/save metadata.
- PLAYBOOK.md: instructions for actually playing the game.
- adapter.py: optional game-specific automation when generic mouse/keyboard/screenshot control is insufficient.

Use game_bridge/games/_template as the starting point for new games.

A play cycle is:

observe -> understand state -> choose action -> execute -> observe again -> persist/recover

For turn-based games, never end the turn until mandatory choices and active-unit/city decisions have been checked. For real-time games, profiles should define safe pause points.

## Validate a game profile

    python game_bridge/game_driver.py validate game_bridge/games/unciv/profile.json

## Create a request

Copy queue.example.json to queue.json, change its request id/URL, and commit it on the game-agent-bridge branch. The push workflow processes the queue.

After this feature is merged to the repository default branch, workflow_dispatch can also be used from the Actions UI.

## Adding a new game

See game_bridge/games/README.md. The important rule is to document both mechanics and operating procedure. "How to win" is not enough: the agent needs to know how to start the executable, recognize menus, take screenshots, issue controls, find saves, detect a completed action, recover from mistakes, and know which actions require user confirmation.
