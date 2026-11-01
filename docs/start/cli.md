---
myst:
  html_meta:
    "description": "The path for people at a terminal: read a Plone site with one command, then follow the steps to managing and scripting many sites."
    "property=og:description": "The path for people at a terminal: read a Plone site with one command, then follow the steps to managing and scripting many sites."
    "property=og:title": "Manage sites from a terminal"
---

(start-cli)=

# Manage sites from a terminal

At the end of this path, you will have your sites registered as {term}`profiles <profile>`, you will publish content in bulk after previewing it, and you will have recipes for everyday jobs.

## Try it now

This command searches [`demo.plone.org`](https://demo.plone.org), a public site that resets every night, without logging in.

<!-- check: start -->
<!-- demo-site: provisional -->
<!-- check: demo -->
```shell
uvx --from "plone-client[cli]" plone-client --url https://demo.plone.org search -q Plone --limit 3 -f title,@type
```

<!-- check: stop -->

## You need

- [uv](https://docs.astral.sh/uv/).
- [Docker](https://www.docker.com/), from the second step on.
- No Plone knowledge: {doc}`index` has what you need.

## Follow these steps

1. {ref}`howto-install` gives you a permanent `plone-client` command, because `uvx` downloads it each time.
2. {ref}`tutorial-first-cli-session` is the core of the path: you add a read-only profile, a local one, and publish in bulk.
3. {ref}`howto-profiles` adds your own sites, and keeps their secrets where you want them.
4. {ref}`howto-preview-changes` shows the difference between a dry run and a read-only profile.
5. {ref}`howto-everyday` has a recipe for the common jobs.
6. {ref}`howto-scripts-ci` takes the same commands to scripts and scheduled jobs.

## Going further

- {ref}`reference-cheat-sheet` lists the commands by task, on one page.
- {ref}`reference-cli` has every option of every command.
- {ref}`reference-services` shows the command for each service.

## If something breaks

{ref}`howto-troubleshoot` goes from the symptom to the fix.

## Keep the site safe

Add `--read-only` to the profile of a production site, and add `-n` to a command to see what it would send; see {ref}`howto-preview-changes`.
