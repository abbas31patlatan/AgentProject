# Agent-scoped request inbox

Each agent creates immutable request files below:

`<agent-id>/<request-id>.json`

Do not share a mutable queue between agents. The worker scans this inbox and writes the matching response to:

`game_bridge/responses/agents/<agent-id>/<request-id>.json`

See `game_bridge/coordination/PROTOCOL.md` section 9.
