# Unciv playbook

This profile describes the desktop Unciv runtime currently used by the agent.

## Boot

The game is launched under a virtual X display. On a clean first launch, choose a language and continue. English is useful for consistent UI recognition. The main menu normally exposes Resume, Quickstart, New Game, Multiplayer, Map Editor, Mods, Options, Civilopedia and Exit.

The current controller accepts screenshot-independent input commands such as click, move, key, hotkey, text, scroll and wait. Always capture a fresh screenshot before acting if the visible state may have changed.

## Starting safely

For disposable testing, Quickstart is the fastest path. For a persistent campaign, use New Game and verify civilization/map/difficulty settings before starting. Do not overwrite a user save without explicit confirmation.

Tutorial popups can cover the map. Read/dismiss them before issuing map clicks so coordinates are not applied to the wrong UI layer.

## What to inspect every turn

Before ending a turn, check:

- Current civilization, year and turn number.
- Any modal popup or required choice.
- Active units and units still needing orders.
- City production and growth status.
- Research selection/progress.
- Gold and happiness/empire-wide constraints visible in the top UI.
- Diplomacy/notifications that require a response.
- Strategic map information relevant to the immediate plan.

A screenshot after an important click is the normal verification mechanism.

## Core play loop

Unciv is a turn-based 4X strategy game. The agent should maintain an explicit strategic objective while handling tactical actions each turn.

Typical early-game loop:

1. Evaluate the settler's visible starting tiles. Prefer a strong city location rather than moving blindly; account for food/production, nearby resources and terrain.
2. Found the first city when the location is acceptable.
3. Select initial production and research if the UI requires it.
4. Use the starting military/scout unit to reveal nearby terrain without exposing it needlessly.
5. Recheck mandatory decisions.
6. End Turn only after no important unit/city/research choice has been forgotten.
7. Observe the next turn before planning more actions.

Later turns add expansion, workers/improvements, military, diplomacy, technology choices, social policies and victory planning. The strategic layer should be updated from the actual map rather than from a fixed build order.

## Interaction discipline

Use observe -> act -> observe for consequential actions. Prefer one or a small number of inputs between screenshots when the UI state is uncertain.

Do not rely on stale coordinates after opening a city screen, technology screen, diplomacy dialog, tutorial or other modal. Close or understand the modal first.

For map movement, verify the selected unit and destination before committing. For city production/research choices, verify the selected item appears as the active choice afterward.

## Save and recovery

In the current isolated runtime, Unciv data has been observed under:

- ${GAME_RUNTIME_ROOT}/unciv-runtime/SaveFiles
- ${GAME_RUNTIME_ROOT}/unciv-runtime/GameSettings.json

Before experimental automation or multiplayer save exchange, preserve a copy of the relevant save. After a crash, restart the game, use Resume/load, then capture a screenshot to verify the restored turn.

## Multiplayer / human-agent exchange

Treat save/state synchronization separately from GUI control. A GitHub bridge can carry a save or compact state between players, while the game itself continues locally. Never assume the remote player has taken a turn until the imported save/state visibly reflects it.

## Safe pause point

The preferred handoff point is before End Turn with the current screenshot captured, no modal dialog hiding the map, and no unresolved mandatory choice. This lets another agent or the user inspect the exact state before the turn advances.

## Current smoke-tested path

The environment has already demonstrated this sequence:

launch Unciv -> choose English -> Continue -> main menu -> Quickstart -> live Greece game at 4000 BC.

That proves the basic display, screenshot and mouse-control loop. Future automation should extend from observed states rather than assuming screen coordinates are permanently fixed.
