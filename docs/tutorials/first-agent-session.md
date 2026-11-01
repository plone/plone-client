---
myst:
  html_meta:
    "description": "Give a coding agent a Plone site, first through the plone-client command line and its skill, then through the MCP server."
    "property=og:description": "Give a coding agent a Plone site, first through the plone-client command line and its skill, then through the MCP server."
    "property=og:title": "Your first agent session"
---

(tutorial-first-agent-session)=

# Your first agent session

In this tutorial, we will prepare a project so that a {term}`coding agent` can work on a Plone site.
We will give it a local site it can change, and a second {term}`profile` that it can only read.
Then we will do one task two ways: through the command line, as an agent with the {term}`skill` does, and through the {term}`MCP` server, as an {term}`assistant` does.

At the end you will have a project that any agent can open, and you will know what it can do on each site.

You need [uv](https://docs.astral.sh/uv/), [Docker](https://www.docker.com/), and Python 3.12 or later.
A coding agent is optional: every step runs without one.

<!-- check: start -->

## Start a Plone site

We will work on a throwaway site with {term}`Volto` and sample content, described in {ref}`howto-run-a-site`.
Get the Compose file, and start the site.

<!-- check: skip -->
```shell
curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
```

<!-- check: skip -->
```shell
docker compose up --wait
```

Open `http://localhost:3000` to see the site.
The user is `admin`, and the password is `admin`.

## Install plone-client

Install it as a tool, with the extras for the command line, the MCP server, and Markdown.

<!-- check: skip -->
```shell
uv tool install "plone-client[cli,mcp,markdown]"
```

## Create the profiles yourself

You create the profiles, in your own terminal, so the password goes into your {term}`keyring` and never through the agent.
The first profile is the site the agent may change.

<!-- check: stdin admin -->
```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --description "Local site, safe to change" --use
```

When asked for the password, type `admin`.
To avoid the prompt, keep the password in an environment variable; see {ref}`howto-profiles`.

The second profile stands for your production site.
It points at the same Compose site, so that this tutorial needs only one, and it is {term}`read-only`.

<!-- check: stdin admin -->
```shell
plone-client profile add production --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --description "Stands for production, read only" --read-only
```

## Prepare the project

Make a folder for the project, and go into it.

```shell
mkdir newsroom
```

Point the project at its site with a `.plone-client.toml` file.

<!-- check: file newsroom/.plone-client.toml -->
```toml
profile = "local"
```

Install the skill.

```shell
cd newsroom
plone-client skill install
```

```json
{
  "installed": ".claude/skills/plone-client/SKILL.md",
  "replaced": false
}
```

Notice where it went: `.claude/skills` is where Claude Code looks.
{ref}`howto-agents` names the folder for other agents.

The skill knows the command line, not your sites.
Add what only you know to `AGENTS.md`, which agents read when they open the project.

<!-- check: file newsroom/AGENTS.md -->
```markdown
# Newsroom

- Profiles: `local` is the default and safe to change. `production` is read only: pass `-p production` to read it.
- News goes in `/news`, as `News Item`. If `/news` is missing, create it as a `Document`, because this site cannot add a `Folder`.
- Show me the dry run before you change anything.
```

## Give the agent its task

Open the project in your agent, and ask for this.

```text
Write a short news item about the sprint in Brasília in /news, show me what you
would send, and publish it when I say so.
```

An agent with the skill does this with the commands below.
Run them yourself, in this order, to see what each one prints.
The commands of a real session depend on your agent and on what it finds, so yours may differ.

Find out which site you are on.

```shell
cd newsroom
plone-client info -f profile,url,read_only
```

```json
{
  "profile": "local",
  "url": "http://localhost:8080/Plone",
  "read_only": false
}
```

Look at what is there.

```shell
cd newsroom
plone-client ls /news -f @id,review_state
```

```json
[
  {
    "@id": "http://localhost:8080/Plone/news/release-6-2",
    "review_state": "published"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-party",
    "review_state": "private"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-notes-draft",
    "review_state": "private"
  },
  {
    "@id": "http://localhost:8080/Plone/news/sprint-report",
    "review_state": "pending"
  },
  {
    "@id": "http://localhost:8080/Plone/news/old-announcement",
    "review_state": "published"
  }
]
```

Write the story.

<!-- check: file newsroom/story.md -->
```markdown
# Sprint in Brasília

We spent three days improving the documentation.
Everyone is welcome at the next one.
```

Preview it with `-n`, which the skill asks for before any change.

```shell
cd newsroom
plone-client -n create-page /news story.md --type "News Item" -f operation,dry_run,created
```

```json
{
  "operation": "create_page",
  "dry_run": true,
  "created": [
    {
      "@id": "http://localhost:8080/Plone/news/sprint-in-brasilia",
      "@type": "News Item",
      "id": "sprint-in-brasilia",
      "title": "Sprint in Brasília",
      "planned": true
    }
  ]
}
```

Notice `dry_run` and `planned`: nothing reached the site.
This is the output that you approve.

Now do it for real.

```shell
cd newsroom
plone-client create-page /news story.md --type "News Item" -f item
```

```json
{
  "item": {
    "@id": "http://localhost:8080/Plone/news/sprint-in-brasilia",
    "@type": "News Item",
    "UID": "0d2c7d77e919423fab1b71fe2c8ca9c9",
    "id": "sprint-in-brasilia",
    "title": "Sprint in Brasília",
    "review_state": "private"
  }
}
```

The item is private.
Publish it.

```shell
cd newsroom
plone-client workflow /news/sprint-in-brasilia publish -f review_state
```

```json
{
  "review_state": "published"
}
```

## See the read-only profile refuse

Ask for the same change on production.

<!-- check: exit 7 -->
```shell
cd newsroom
plone-client -p production workflow /news/release-party publish
```

```json
{
  "error": {
    "type": "PloneReadOnlyError",
    "message": "POST /news/release-party/@workflow/publish refused: the client is read-only"
  }
}
```

The command exits with code 7, and the skill tells the agent to stop there and tell you, not to work around it.
Reads still work.

```shell
cd newsroom
plone-client -p production get /news/sprint-in-brasilia -f title,review_state
```

```json
{
  "title": "Sprint in Brasília",
  "review_state": "published"
}
```

## Do the same through the MCP server

A chat assistant has no terminal, so it uses {term}`tools <tool>` that the MCP server offers.
{ref}`howto-assistant` connects a real assistant.
Here, a small script takes its place, so you can see each call and each answer.

<!-- check: file ask.py -->
```python
"""Call one tool of the plone-client MCP server, as an assistant does."""

import asyncio
import json
import os
import shlex
import sys

from mcp import Client
from mcp import StdioServerParameters


async def main(server: str, tool: str, arguments: dict) -> int:
    command = StdioServerParameters(
        command="plone-client", args=shlex.split(server), env=dict(os.environ)
    )
    async with Client(command) as client:
        result = await client.call_tool(tool, arguments)
    print(result.content[0].text)
    return 1 if result.is_error else 0


server, tool, *rest = sys.argv[1:]
sys.exit(asyncio.run(main(server, tool, json.loads(rest[0]) if rest else {})))
```

Start with the tool that every session should start with.

```shell
python ask.py "mcp --profile local --dry-run" site_info
```

```json
{
  "url": "http://localhost:8080/Plone",
  "authenticated": true,
  "username": "admin",
  "credentials_rejected": false,
  "read_only": false,
  "plone_version": "6.1.5",
  "frontend_url": "http://localhost:3000",
  "dry_run": true
}
```

Notice `dry_run`: this server started with `--dry-run`, so the tools that change the site send nothing.
Ask it for a page, as an assistant would.
We use [jq](https://jqlang.org/) to keep only part of the answer.

```shell
python ask.py "mcp --profile local --dry-run" create_page '{"parent": "/news", "portal_type": "News Item", "source": "# Sprint report two\n\nThe second report."}' | jq '{dry_run, created}'
```

```json
{
  "dry_run": true,
  "created": [
    {
      "@id": "http://localhost:8080/Plone/news/sprint-report-two",
      "@type": "News Item",
      "id": "sprint-report-two",
      "title": "Sprint report two",
      "planned": true
    }
  ]
}
```

Now start the server as usual, and the same call creates the item.

```shell
python ask.py "mcp --profile local" create_page '{"parent": "/news", "portal_type": "News Item", "source": "# Sprint report two\n\nThe second report."}' | jq .item
```

```json
{
  "@id": "http://localhost:8080/Plone/news/sprint-report-two",
  "@type": "News Item",
  "UID": "b8549cb5ef5f4b07a9a6f461bda306ed",
  "id": "sprint-report-two",
  "title": "Sprint report two",
  "review_state": "private"
}
```

A server on the read-only profile does not offer the tool at all.

<!-- check: exit 1 -->
```shell
python ask.py "mcp --profile production" create_page '{"parent": "/news", "source": "# No"}'
```

```text
Unknown tool: create_page
```

<!-- check: stop -->

You have a project that an agent can open, a site it can change, a profile it can only read, and the same task done through both doors.

## Clean up

Stop the site, which throws away its content, and remove the profiles and their passwords.

<!-- check: skip -->
```shell
docker compose down -v
plone-client profile remove local
plone-client profile remove production
```

## Next steps

- {ref}`tutorial-editorial-assistant` builds an assistant with images, several sites, and an approval step.
- {ref}`howto-protect` decides what an assistant can see and do.
- {ref}`howto-agents` sets up the skill for each agent.
- {ref}`howto-troubleshoot` helps when something goes wrong.
