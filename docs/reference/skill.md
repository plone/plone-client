---
myst:
  html_meta:
    "description": "The agent skill that ships with plone-client: its full text, where plone-client skill install writes it, and which directories each agent reads."
    "property=og:description": "The agent skill that ships with plone-client: its full text, where plone-client skill install writes it, and which directories each agent reads."
    "property=og:title": "Agent skill"
---

(reference-skill)=

# Agent skill

plone-client ships an [Agent Skill](https://agentskills.io/): a `SKILL.md` file that teaches a {term}`coding agent` its commands, its output, the Volto content model, and the safety rules.
{ref}`howto-agents` installs it.

## Where `skill install` writes

<!-- source: src/plone_client/cli/skill.py -->

| Command | File |
|---|---|
| `plone-client skill install` | `.claude/skills/plone-client/` |
| `plone-client skill install --user` | `~/.claude/skills/plone-client/` |
| `plone-client skill install --dir DIR` | `DIR/plone-client/` |

The folder holds `SKILL.md`, which an agent reads first, and `references/blocks.md`, which it reads when it works with {term}`blocks <block>`.
The command replaces an older copy, and prints `installed`, with the path of `SKILL.md`, and `replaced`.
`plone-client skill show` prints `SKILL.md`, and `plone-client skill show references/blocks.md` prints the reference.

## Directories each agent reads

<!-- source: the documentation of each agent, read on 2026-10-31 -->

| Agent | In a project | For a user |
|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `.claude/skills` | `~/.claude/skills` |
| [Codex](https://learn.chatgpt.com/docs/build-skills) | `.agents/skills`, from the working directory up to the repository root | `~/.agents/skills` |
| [Cursor](https://cursor.com/docs/skills) | `.agents/skills`, `.cursor/skills`, and, for compatibility, `.claude/skills`, `.codex/skills` | `~/.agents/skills`, `~/.cursor/skills`, and, for compatibility, `~/.claude/skills`, `~/.codex/skills` |
| [Gemini CLI](https://geminicli.com/docs/cli/skills) | `.agents/skills`, `.gemini/skills` | `~/.agents/skills`, `~/.gemini/skills` |
| [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) | `.agents/skills`, `.claude/skills`, `.github/skills` | `~/.agents/skills`, `~/.claude/skills`, `~/.copilot/skills` |

## The skill

```{literalinclude} ../../src/plone_client/skill/SKILL.md
:language: markdown
```

## The reference on blocks

```{literalinclude} ../../src/plone_client/skill/references/blocks.md
:language: markdown
```

## Related

- {ref}`howto-agents` sets up a coding agent.
- {ref}`explanation-cli-for-agents` explains why a command line suits agents.
- {ref}`howto-protect` lists what the skill's rules can and cannot enforce.
