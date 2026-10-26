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

## Tell the agent how to use it

Add a section like this one to the project's `CLAUDE.md`, `AGENTS.md`, or equivalent, with your profile names and paths.

````markdown
## Managing the site's content

Use the `plone-client` command line to read and change content on the Plone site.
Never call the REST API with curl, and never ask for passwords: the profiles already hold them.

- Profiles: `blog-local` (local development, the default) and `blog` (production, read-only).
  Pass `-p blog` to read production.
- Output is JSON. Use `-f` to keep only the keys you need, for example `-f @id,title,review_state`.
- Before any change on a site other than `blog-local`, run the command with `-n` first and show me the requests.
- Never pass `--yes` to `delete` without my explicit confirmation of the items to delete.
- Exit codes: 3 configuration, 4 not allowed or locked, 5 not found, 6 invalid request, 7 read-only, 8 site unreachable, 9 server error.
- `plone-client types <type>` shows the fields a content type accepts.

Common commands:

```shell
plone-client ls /blog -f @id,title,review_state
plone-client search -q "keyword" -t Document --limit 10 -f @id,title
plone-client get /blog/post -f title,description,subjects,review_state
plone-client blocks /blog/post
plone-client create /blog Document --title "Title" --description "Summary"
plone-client update /blog/post -s subjects:='["plone"]'
plone-client workflow /blog/post publish
plone-client upload /blog/post image.png
plone-client request GET /@service-without-a-command
```
````

## Related

- {ref}`explanation-cli-for-agents` explains why a command line suits agents.
- {ref}`howto-preview-changes` covers `-n` and `--read-only`.
- {ref}`reference-cli` lists every command and exit code.
