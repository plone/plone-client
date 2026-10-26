# Use it from a coding agent

A coding agent can manage a Plone site through `plone-client` the same way it runs `git` or `make`.
Compared with an MCP server, there is nothing to run in the background, the same commands work for the people on the project, and the agent never sees a password.

## Why it suits agents

- Results are JSON on standard output, and errors JSON on standard error, so nothing has to be scraped from text.
- Exit codes say what went wrong without parsing the message; see [the table](cli.md#errors-and-exit-codes).
- Secrets stay in the keyring.
  The agent selects a site by profile name, and the password never appears in its context.
- `--read-only` profiles make a production site safe to explore.
- `--dry-run` shows the exact requests a change would send.
- Destructive commands refuse to run without `--yes` when there is no terminal, so an agent cannot delete by accident.
- `-f` keeps only the keys the agent needs, which keeps large answers out of its context.

## Set up a project

Create the profiles yourself, once, so the secrets go into your keyring rather than through the agent.

```shell
plone-client profile add blog-local --url http://localhost:8080/Plone --username admin
plone-client profile add blog --url https://example.org --username editor --read-only
```

Point the project at its default profile with a `.plone-client.toml` file at its root.

```toml
profile = "blog-local"
```

## Instructions to paste

Add a section like this one to the project's `CLAUDE.md`, `AGENTS.md`, or equivalent.
Adjust the profile names and the paths.

````markdown
## Managing the site's content

Use the `plone-client` command line client to read and change content on the Plone site.
Never call the REST API with curl, and never ask for passwords: the profiles already hold them.

- Profiles: `blog-local` (local development, the default) and `blog` (production, read-only).
  Pass `-p blog` to read production.
- Output is JSON. Use `-f` to keep only the keys you need, for example `-f @id,title,review_state`.
- Before any change on a site other than `blog-local`, run the command with `-n` first and show me the requests.
- Never pass `--yes` to `delete` without my explicit confirmation of the items to delete.
- Exit codes: 3 configuration, 4 not allowed or locked, 5 not found, 6 invalid request, 7 read-only, 8 site unreachable, 9 server error.

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
plone-client types Document
plone-client request GET /@service-without-a-command
```
````

## When an agent needs more

Run `plone-client --help`, or `plone-client <command> --help`, for every option.
For services that have no command, `plone-client request` reaches any endpoint of plone.restapi, and `plone-client types <type>` shows the JSON schema of a content type, which tells the agent which fields it can set.
