# MCP servers

## Purpose
Inventory all MCP servers, exposed resources, tools, and trust boundaries used by this repo.

## Current state
The bootstrap version of autoharness does not require any repo-specific MCP servers. Core verification and runtime behavior must remain functional without MCP availability.

## Trust boundary
- Candidate execution, evaluator logic, and verifier gates must not depend on MCP tools.
- Any future MCP integration must be optional, documented here, and kept outside the required verifier path unless the active spec explicitly promotes it.

## Future additions
Any new MCP server entry must document:
- purpose and owner
- transport and auth model
- tools, resources, and prompts exposed
- approval boundaries and likely failure modes
- how the server affects verification and rollback
