# Game profiles

Each supported game gets its own directory. A profile is deliberately split into machine-readable facts and a human/agent playbook.

## Minimum files

profile.json tells the runtime how the game behaves operationally.

PLAYBOOK.md tells the agent how to interact with and play it.

adapter.py is optional. Add one when screenshots plus generic mouse/keyboard controls are not enough, or when the game exposes a richer API.

## Adding a new game

1. Copy the _template directory to a new lowercase game id.
2. Fill profile.json.
3. Write PLAYBOOK.md using actual observed menus and controls, not guesses.
4. Record save locations and whether autosave exists.
5. Define safe pause points. Turn-based games normally pause before End Turn. Real-time games should state how to pause.
6. Define irreversible actions that should require explicit confirmation, such as deleting saves, spending real money, account actions, or overwriting a campaign.
7. Validate the profile with game_driver.py.
8. Run a smoke test: launch -> screenshot -> one reversible input -> screenshot -> save/recover.

## What PLAYBOOK.md should contain

A good playbook covers:

- First launch and language/setup screens.
- Main menu and game-start flow.
- Observation loop: what must be checked before acting.
- Control semantics: clicks, keys, drag behavior, camera movement.
- Core game rules and objective.
- Turn/tick loop.
- Save/load and crash recovery.
- Modal dialogs and tutorials.
- How to detect success/failure of an action.
- Multiplayer or hotseat behavior when applicable.
- Known UI traps and destructive actions.
- A short checklist for every decision cycle.

This makes the system portable. A future game can be added as data and instructions first, then given a custom adapter only if necessary.
