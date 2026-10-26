# Use the command line client

`plone-client` manages the content and settings of Plone sites from a terminal, a shell script, or a coding agent.
Install it with the `cli` extra.

```shell
uv tool install "plone-client[cli]"
```

Create a profile for each site before anything else; see {doc}`profiles`.
Every command then works against the current profile, or against the one named with `-p`.

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --use
plone-client info
plone-client -p prod ls /news
```

## Output

Commands print JSON on standard output.
Commands that create or change an item print a summary of it, with `@id`, `@type`, `UID`, `id`, `title` and `review_state`; pass `--full` for the whole item.

`-f`, `--fields`
: Keeps only some keys.
  It applies to an item, to each item of a list, and to each entry of a folder's or a search's `items`.

`-c`, `--compact`
: Prints each result on a single line.

```shell
plone-client ls /news -f @id,title,review_state
plone-client search -t Document -c | jq -r '.[]["@id"]'
```

Global options can go anywhere on the command line, before or after the command.

## Errors and exit codes

Errors go to standard error as JSON.

```json
{
  "error": {
    "status_code": 404,
    "type": "NotFound",
    "message": "Resource not found: https://example.org/++api++/missing",
    "method": "GET",
    "url": "https://example.org/++api++/missing"
  }
}
```

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | unexpected error |
| 2 | invalid usage, or a change that needs `--yes` |
| 3 | configuration: unknown profile, missing secret, no site configured |
| 4 | not authenticated, not allowed, or the item is locked |
| 5 | not found |
| 6 | invalid request or conflict |
| 7 | refused by a read-only profile or `--read-only` |
| 8 | the site could not be reached |
| 9 | server error |

## Read content

```shell
plone-client get /news/hello
plone-client get /news --no-items --expand breadcrumbs
plone-client ls /news -t "News Item" --limit 20
plone-client search /news -q plone --state published --sort-on effective --reverse
plone-client search -i Subject=release -i 'created:={"query": "2026-01-01", "range": "min"}'
plone-client search -t Document --count
plone-client resolve uid:a2c1e1e88b3e4c3c8f0a1e2d3c4b5a69
plone-client blocks /news/hello --links
plone-client history /news/hello
```

Wherever a command expects an item, it accepts a path, a URL inside the site, `uid:<UID>` or a `resolveuid` link.

## Change content

```shell
plone-client create /news "News Item" --title "Hello" --description "First news" --publish publish
plone-client create /news Document --id about --title About -s subjects:='["plone"]' -d @page.json
plone-client update /news/hello --title "Hello, Plone" -s exclude_from_nav:=true
plone-client workflow /news/hello
plone-client workflow /news/hello retract --comment "Needs review"
plone-client copy /news/hello --to /archive
plone-client move /news/about /news/hello --to /archive
plone-client order /news hello top
plone-client delete /archive/hello --yes
```

Field values come from three places, merged in this order.

1. `-d`, `--data`: a JSON object, `@file.json` to read a file, or `-` to read standard input.
2. `--title` and `--description`.
3. `-s`, `--set`, repeatable: `key=text` sets a string, and `key:=json` sets any JSON value.

`create` adds a title block and a description block to pages created without blocks, as Volto does; pass `--no-blocks` to leave them out.

`order` takes the folder, the item id and where to move it: `top`, `bottom`, `up`, `down`, or a signed number of positions.

## Files

```shell
plone-client upload /images photo.jpg logo.png
plone-client upload /files video.mp4 --tus
plone-client download /images/photo.jpg -o photo.jpg
```

## Safety

`--read-only`
: Refuses every change, before anything is sent.
  A profile created with `--read-only` always behaves this way.

`-n`, `--dry-run`
: Prints the requests a command would send, and sends none of them.

`delete`, and the other commands that remove something, ask for confirmation.
Without a terminal there is nobody to ask, so they need `--yes`.

## Site administration

```shell
plone-client types
plone-client types Document
plone-client vocabulary plone.app.vocabularies.Keywords
plone-client sharing /news
plone-client registry get plone.site_title
plone-client registry set plone.site_title '"My site"'
plone-client users list
plone-client users create jane --email jane@example.org --role Editor
plone-client users create bot --email bot@example.org --password-stdin < password.txt
plone-client groups add-member Reviewers jane
plone-client aliases add /news/hello /old/hello
```

`users create` asks the site to email the new user a link to set a password, which needs a configured mail server.
`--password-stdin` sets the password instead, read from standard input so it stays out of the shell history.

## Other services

`request` sends any request to the site, for services without a command.

```shell
plone-client request GET /@my-addon-service -P query=value
plone-client request POST /news/hello/@my-action -d '{"key": "value"}'
```

## Shell completion

```shell
plone-client --install-completion
```
