---
myst:
  html_meta:
    "description": "Why plone-client offers coding agents a command line, and what makes it safe for them."
    "property=og:description": "Why plone-client offers coding agents a command line, and what makes it safe for them."
    "property=og:title": "About the command line for coding agents"
---

(explanation-cli-for-agents)=

# About the command line for coding agents

Coding agents such as Claude Code work by running commands in a terminal.
They already run `git`, `make`, and test suites, read the output, and decide what to do next.
A command line for Plone fits into that loop without anything new to set up.

## A command line or an MCP server

The Model Context Protocol (MCP) is another way to give an agent access to a system: a server that exposes tools the agent can call.
It suits services the agent cannot otherwise reach.

For a Plone site, a command line has practical advantages.
There is nothing to keep running in the background, nothing to configure per agent, and nothing different between what the agent runs and what a person runs.
When an agent does something unexpected, you can read the exact command in its transcript and run it yourself.
The same commands also serve shell scripts and CI jobs, so one tool covers all three.

An MCP server still has its place.
Chat assistants without a terminal can only reach a site through one, so plone-client ships one too, built on the same library and profiles; {ref}`explanation-interfaces` compares the two.

## Why a skill

An agent that has never seen plone-client learns it from `--help`, one command at a time, and has no way to know the conventions of the site behind it: that Volto sites have no `Folder` type, or that a field a type does not have is silently ignored.
The agent skill shipped with plone-client gives it all of that at once, together with the rules a careful person would follow: preview a change before making it, and never delete without confirmation.
The skill is loaded only when a task needs it, so it costs nothing the rest of the time.

## What makes it safe

An agent should not see passwords, and should not be able to break a production site by accident.
Several properties of plone-client work together for that.

- Profiles keep secrets in the keyring.
  The agent picks a site by name, and the password never enters its context.
- Read-only profiles make production safe to explore, because every change is refused before it is sent.
- `-n` shows the exact requests a change would send, so a person can review them before anything happens.
- Destructive commands refuse to run without `--yes` when there is no terminal to ask in, and an agent has none.

## What makes it efficient

An agent pays for every token it reads.
Results are JSON, so the agent never scrapes text, and `-f` keeps only the keys it needs, which keeps large answers out of its context.
Errors are JSON with a distinct exit code per kind of failure, so the agent can tell "not found" from "not allowed" without reading the message.

## Related

- {ref}`howto-agents` sets up a project for an agent.
- {ref}`explanation-secrets` explains where secrets go.
