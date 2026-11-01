---
myst:
  html_meta:
    "description": "Let a coding agent such as Claude Code, Codex, Cursor, Copilot, or Gemini CLI manage a Plone site through the plone-client command line and its skill."
    "property=og:description": "Let a coding agent such as Claude Code, Codex, Cursor, Copilot, or Gemini CLI manage a Plone site through the plone-client command line and its skill."
    "property=og:title": "Use plone-client with coding agents"
---

(howto-agents)=

# Use plone-client with coding agents

This guide shows you how to let a {term}`coding agent` read and change a Plone site through the command line, without giving it your passwords.
It works with any agent that can run a command.
An agent needs three things: the `plone-client` command on its path, {term}`profiles <profile>` that you created, and a {term}`skill` file in a directory it reads.

If your agent has no shell, connect it through the {term}`MCP` server instead, as {ref}`howto-assistant` shows.
To follow all of this step by step on a throwaway site, take {ref}`tutorial-first-agent-session`.

## Create the profiles yourself

Create the profiles in your own terminal, so the secrets go into your {term}`keyring` and never through the agent.
Make every site other than your local one {term}`read-only`.

```shell
plone-client profile add blog-local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000
plone-client profile add blog --url https://example.org --username editor --read-only
```

## Point the project at its profile

Add a `.plone-client.toml` file at the root of the project.

```toml
profile = "blog-local"
```

## Install the agent skill

plone-client ships an [Agent Skill](https://agentskills.io/home) that teaches an agent its commands, output, exit codes, the {term}`Volto` content model, and the safety rules: no passwords, a {term}`dry run` before changes, and no deletion without your confirmation.
{ref}`reference-skill` shows its full text.

Install it in the directory your agent reads, at the root of the project.

::::{tab-set}
:sync-group: agent

:::{tab-item} Claude Code
:sync: claude-code

```shell
plone-client skill install
```

This writes `.claude/skills/plone-client/SKILL.md`.
:::

:::{tab-item} Codex
:sync: codex

```shell
plone-client skill install --dir .agents/skills
```
:::

:::{tab-item} Cursor
:sync: cursor

```shell
plone-client skill install --dir .agents/skills
```

Cursor also reads `.cursor/skills`, and `.claude/skills` for compatibility.
:::

:::{tab-item} VS Code
:sync: copilot

```shell
plone-client skill install --dir .agents/skills
```

GitHub Copilot in VS Code also reads `.github/skills` and `.claude/skills`.
:::

:::{tab-item} Gemini CLI
:sync: google

```shell
plone-client skill install --dir .agents/skills
```

Gemini CLI also reads `.gemini/skills`.
:::
::::

Commit the file to share it with everyone working on the project.

To install it for every project instead, pass the directory in your home.
{ref}`reference-skill` lists these per agent.

```shell
plone-client skill install --user
plone-client skill install --dir ~/.agents/skills
```

`--user` writes to `~/.claude/skills`.

Run the command again after upgrading plone-client, to replace the skill with the new version.

## Use an agent without skill support

Print the skill, and paste it into the agent's rules or its first message.

```shell
plone-client skill show
```

## Tell the agent about your sites

The skill knows the command line, not your sites.
Add what only you know to the file your agent reads for the project, such as `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`.
Start from this template.

```markdown
# Plone sites

## Profiles

- `blog-local` is the local site and the default. You may change it.
- `blog` is production, and it is read only. Pass `-p blog` to read it.
- If a command exits with code 7, tell me. Do not work around it.

## Content

- News goes in `/blog`, as `News Item`, published with the `publish` transition.
- Documentation goes in `/docs`, as `Document`.

## Rules

- Never ask me for a password, and never call the REST API with `curl`.
- Never create or remove profiles unless I ask.
- Run a change with `-n` first, and show me the output.
- Delete nothing unless I confirmed the exact items.
```

## Related

- {ref}`howto-protect` limits what an agent can do, and says what the rules above cannot enforce.
- {ref}`explanation-cli-for-agents` explains why a command line suits agents.
- {ref}`howto-preview-changes` covers `-n` and `--read-only`.
- {ref}`reference-cli` lists every command and exit code.
