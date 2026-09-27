# Agent-scoped bridge responses

Responses are published as:

`<agent-id>/<request-id>.json`

A response includes the canonical hash of its immutable request. Small text payloads may be embedded inline; larger files are referenced through the workflow artifact for that run.
