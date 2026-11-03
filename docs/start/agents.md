---
myst:
  html_meta:
    "description": "The path for assistants and coding agents: choose between the skill and the MCP server, then follow the steps to a model that edits a Plone site within limits."
    "property=og:description": "The path for assistants and coding agents: choose between the skill and the MCP server, then follow the steps to a model that edits a Plone site within limits."
    "property=og:title": "Work with assistants and coding agents"
---

(start-agents)=

# Work with assistants and coding agents

At the end of this path, you will have an assistant or a {term}`coding agent` that prepares content on a {term}`Plone` site, previews its changes, and cannot touch what you protected.

## Choose how your model reaches the site

Where your model runs decides what to set up.

| Your model runs | Use | Start with |
|---|---|---|
| In a terminal or an editor, such as Claude Code, Codex, or Cursor | The {term}`skill` and the command line | {ref}`howto-agents` |
| In Claude Desktop | The {term}`MCP` server, over standard input and output | {ref}`howto-claude-desktop` |
| In another chat application | The MCP server, over standard input and output | {ref}`howto-assistant` |
| On another computer, or shared by a team | The MCP server, over HTTP | {ref}`howto-assistant` |
| In your own code | The Python library | {ref}`howto-custom-agent` |

## Skill or MCP server

<!-- source: src/plone_client/skill/SKILL.md, src/plone_client/mcp_server.py -->

| | Skill and command line | MCP server |
|---|---|---|
| What it is | A file that teaches the agent the commands | A process that offers {term}`tools <tool>` |
| Who runs the commands | The agent, in its shell | The server |
| What the model sees | The skill, and each command's output | The tool list and the server's {term}`instructions` |
| What limits it | The {term}`profile`, and the agent's own permissions | The profile, and the tools you offer with `--tool` |
| Pick it when | The agent already has a terminal | There is no terminal, or the agent must not run arbitrary commands |

`call_service` is offered in every mode, read-only included, because it reaches every service the user can use; none of the tool sets this documentation recommends includes it.

{ref}`explanation-interfaces` explains the difference at length.

## You need

- Python 3.12 or later, for the `markdown` extra that turns Markdown into pages.
- [uv](https://docs.astral.sh/uv/).
- [Docker](https://www.docker.com/), for the local site that the tutorials change.
- An assistant or a coding agent.

## Follow these steps

1. {ref}`howto-install` adds the `mcp` and `markdown` extras, because the server and its Markdown pages need them.
2. {ref}`tutorial-first-agent-session` gives an agent a site, first through the command line and then through the MCP server.
3. {ref}`howto-protect` decides what your model can see and do, before you point it at a real site.
4. {ref}`howto-assistant` or {ref}`howto-agents` connects the tool you use.
5. {ref}`tutorial-editorial-assistant` builds a complete assistant for two sites.

## Going further

- {ref}`reference-assistant-server` lists every tool and resource.
- {ref}`reference-skill` shows what the skill says.
- {ref}`reference-content-model` shows what a model must know to write a page.

## If something breaks

{ref}`howto-troubleshoot` goes from the symptom to the fix.

## Before you connect a real site

- Log in as a dedicated Plone user with only the permissions the model needs, not `admin`.
- Add the site first as a read-only {term}`profile`, with `--read-only`.
- Start the server with `--dry-run` for the first session that writes, and read the planned requests; see {ref}`howto-preview-changes`.
- Keep the password in the {term}`keyring`, or use `--secret env` or `--secret command` where there is none; see {ref}`howto-scripts-ci`.
- Offer only the tools the job needs with `--tool`, and read {ref}`howto-protect` before you give a model write access.
