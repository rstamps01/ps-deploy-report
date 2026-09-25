---
name: Restore Atlassian MCP
overview: Re-enable and re-authorize the plugin-provided Atlassian (Confluence/Jira) MCP server for the vast-asbuilt-reporter workspace, which is currently not registered for this project.
todos:
  - id: enable-plugin
    content: "User: enable the Atlassian plugin's MCP server for the vast-asbuilt-reporter workspace in Cursor Settings"
    status: pending
  - id: run-mcp-auth
    content: After registration, run mcp_auth for plugin-atlassian-atlassian to complete OAuth
    status: pending
  - id: verify-connection
    content: Verify by listing Atlassian tools and reading Confluence page 6664028496
    status: pending
isProject: false
---

# Restore Atlassian Confluence MCP Connection

## Root cause

The Atlassian MCP is a **plugin-provided OAuth remote server** (`cursor-public/atlassian` plugin, server id `plugin-atlassian-atlassian`), not a local entry in `~/.cursor/mcp.json`. MCP servers are registered **per-workspace**. This workspace's folder `~/.cursor/projects/Users-ray-stamps-vast-asbuilt-reporter/mcps/` has no `plugin-atlassian-atlassian` directory and `atlassian` is absent from the session's available servers, so the server is **disabled/unregistered for this project**. Other projects have it registered but their `STATUS.md` shows it also needs re-authentication (OAuth lapsed).

## What requires the user (UI actions I cannot perform)

- Enabling a plugin/MCP toggle and completing the browser OAuth flow are Cursor Settings actions outside agent control.

### User steps

1. Open Cursor Settings -> MCP & Integrations (or Plugins).
2. Confirm the Atlassian plugin is installed (it is) and **enable its MCP server for this workspace** (`vast-asbuilt-reporter`). This causes Cursor to register `plugin-atlassian-atlassian` and create its folder under this project's `mcps/`.
3. If an "Authenticate"/"Login" / "Needs login" control appears, click it and complete the Atlassian OAuth in the browser. If it shows "errored," toggle off/on or restart Cursor, then retry.

## What I can do once enabled

- After the server is registered for this workspace, I will run the `mcp_auth` tool for `plugin-atlassian-atlassian` (empty args) to launch/complete OAuth, then verify by listing its tools (e.g. `getConfluencePage`, `searchConfluenceUsingCql`) and making a read call against Confluence page `6664028496` referenced in the project rules.

## Verification

- `~/.cursor/projects/Users-ray-stamps-vast-asbuilt-reporter/mcps/plugin-atlassian-atlassian/STATUS.md` no longer says "needs authentication."
- `atlassian` tools appear in available MCP servers and a Confluence read succeeds.

## Notes

- No repository code changes are involved; this is Cursor app/MCP configuration only.
- If the workspace toggle is intentionally project-scoped, alternatively the plugin can be enabled globally so all workspaces inherit it.
