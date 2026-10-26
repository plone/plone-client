---
myst:
  html_meta:
    "description": "Let a coding agent such as Claude Code manage a Plone site through the plone-client command line, safely."
    "property=og:description": "Let a coding agent such as Claude Code manage a Plone site through the plone-client command line, safely."
    "property=og:title": "Use plone-client with coding agents"
---

(howto-agents)=

# Use plone-client with coding agents

This guide shows you how to let a coding agent read and change a Plone site through the command line, without giving it your passwords.

## Create the profiles yourself

Create the profiles in your own terminal, so the secrets go into your keyring and never through the agent.
Make every site other than your local one read-only.

```shell
plone-client profile add blog-local --url http://localhost:8080/Plone --username admin
plone-client profile add blog --url https://example.org --username editor --read-only
```

## Point the project at its profile

Add a `.plone-client.toml` file at the root of the project.

```toml
profile = "blog-local"
```

## Install the agent skill

plone-client ships an [Agent Skill](https://agentskills.io/) that teaches an agent its commands, output, exit codes, the Volto content model, and the safety rules: no passwords, a dry run before changes, and no deletion without your confirmation.

To install it in the project, run this at the project's root.

```shell
plone-client skill install
```

It writes `.claude/skills/plone-client/SKILL.md`, where Claude Code finds it.
Commit the file to share it with everyone working on the project.

To install it for every project instead, pass `--user`; it then goes in `~/.claude/skills`.

```shell
plone-client skill install --user
```

For an agent that reads skills from another directory, pass it with `--dir`.

```shell
plone-client skill install --dir .agents/skills
```

Run `plone-client skill install` again after upgrading plone-client, to replace the skill with the new version.
To read the skill, or to paste it into an agent without skill support, print it.

```shell
plone-client skill show
```

## Tell the agent about your sites

The skill knows the command line, not your sites.
Add what only you know to the project's `CLAUDE.md`, `AGENTS.md`, or equivalent.

```markdown
## Plone sites

- Profiles: `blog-local` (local development, the default) and `blog` (production, read-only).
  Pass `-p blog` to read production.
- News goes in `/blog`, as `News Item`, published with the `publish` transition.
```

## Related

- {ref}`explanation-cli-for-agents` explains why a command line suits agents.
- {ref}`howto-preview-changes` covers `-n` and `--read-only`.
- {ref}`reference-cli` lists every command and exit code.
