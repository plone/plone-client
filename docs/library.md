# Use the library

This guide walks through {class}`~plone_client.PloneClient`, from connecting to a site to changing its content.

## Connect

Create a client with the URL of the site root and the credentials of a user.
Use it as a context manager, so its connections are closed at the end.

```python
from plone_client import PloneClient

with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as client:
    site = client.content.get("/")
    print(site["title"])
```

The client sends HTTP basic authentication by default.
Pass `auth_method="jwt"` to log in through `@login` instead.
The client then sends the token it receives, and logs in again when the token expires.
A JWT issued beforehand goes in `token`.

```python
client = PloneClient(url, username="admin", password="admin", auth_method="jwt")
client = PloneClient(url, token="eyJhbGciOi...")
```

Two class methods read the settings from elsewhere.

{meth}`~plone_client.PloneClient.from_env`
: Reads `PLONE_CLIENT_URL`, `PLONE_CLIENT_USERNAME`, `PLONE_CLIENT_PASSWORD` and the other variables listed in `.env.example`.
  Pass `prefix="REMOTE_"` to read `REMOTE_URL`, `REMOTE_USER` and `REMOTE_PASSWORD` instead.

{meth}`~plone_client.PloneClient.from_profile`
: Reads a profile created with the command line client, and its secret from the keyring.
  See {doc}`profiles`.

Keyword arguments passed to either method win over the settings they read.

```python
client = PloneClient.from_env(prefix="REMOTE_", read_only=True)
```

## Refer to items

Every method that takes an item accepts any of these references.

- A path from the site root, such as `/news/hello`.
- A full URL inside the site, such as an `@id` returned by an earlier call.
- `uid:` followed by the item's UID.
- A `resolveuid` link, such as `../resolveuid/<UID>`, as found inside blocks.

UID references cost one extra `@search` request each.
A URL outside the site raises {class}`ValueError`.

## Read content

```python
item = client.content.get("/news/hello")
item = client.content.get("/news", include_items=False, expand=["breadcrumbs"])
item = client.content.find_by_uid("a2c1e1e88b3e4c3c8f0a1e2d3c4b5a69")

for child in client.content.children("/news"):
    print(child["@id"], child["title"])
```

{meth}`~plone_client.managers.content.ContentManager.children` returns the items of a folder in the folder's order.
Like the search methods, it returns catalog entries, not full serializations, and fetches them page by page.

## Search

{meth}`~plone_client.managers.search.SearchManager.iter` goes through every page of results and stops after `limit` items, if given.
{meth}`~plone_client.managers.search.SearchManager.search` returns a single page as plone.restapi sends it, and {meth}`~plone_client.managers.search.SearchManager.count` only the number of results.

```python
for item in client.search.iter(
    "/news",
    portal_type="News Item",
    review_state="published",
    sort_on="effective",
    sort_order="descending",
    metadata_fields=["effective", "Subject"],
    limit=20,
):
    print(item["effective"], item["title"])

client.search.count(portal_type="Document")
client.search.iter(query={"Subject": "plone", "path.depth": 1})
```

Indexes without a keyword argument go in `query`.
Nested values are flattened the way plone.restapi expects, so `{"created": {"query": "2026-01-01", "range": "min"}}` becomes `created.query=2026-01-01&created.range=min`.

`client.querystring.search()` runs the same queries as Volto's listing and search blocks.

## Change content

```python
from plone_client import blocks

item = client.content.create(
    "/news",
    "News Item",
    id="hello",
    title="Hello",
    description="The first news item",
    subjects=["plone"],
    **blocks.build(blocks.title(), blocks.description(), blocks.text("Welcome.")),
)

client.content.update(item["@id"], description="Changed")
client.workflow.transition(item["@id"], "publish", effective="2026-11-01T09:00:00")
client.content.move(item["@id"], "/archive")
client.content.delete("/archive/hello")
```

Plone may change the id you ask for, so read the `@id` of the created item instead of building the path yourself.

{mod}`plone_client.blocks` builds the `blocks` and `blocks_layout` fields of a Volto page.
{func}`~plone_client.blocks.iter_blocks` walks every block, nested ones included, and {func}`~plone_client.blocks.iter_links` finds the links inside them.

## Upload files

```python
image = client.files.upload("/images", "photo.jpg", title="A photo")
client.files.replace(image["@id"], "photo-2.jpg")
data = client.files.download(image["@id"])
```

{meth}`~plone_client.managers.files.FilesManager.upload` creates an `Image` for image files and a `File` for anything else.
The file travels base64 encoded inside the JSON body.
For large files, {meth}`~plone_client.managers.files.FilesManager.tus_upload` sends the file in chunks through plone.restapi's TUS support.

## Make automation safe

`read_only=True`
: Refuses every request that could change the site, and raises {class}`~plone_client.exceptions.PloneReadOnlyError` before anything is sent.
  Searches through `@querystring-search` and logins still work.

`dry_run=True`
: Records changing requests in `client.dry_run_log` instead of sending them, while reads still go to the site.
  Each skipped request returns a description of itself instead of the site's answer, so code that reads the `@id` of a created item must handle a missing value.

## Handle errors

```python
from plone_client import PloneClientError
from plone_client import PloneNotFoundError

try:
    client.content.get("/missing")
except PloneNotFoundError as error:
    print(error.status_code, error.message)
except PloneClientError as error:
    print(f"Something else went wrong: {error}")
```

Errors returned by the site are subclasses of {class}`~plone_client.exceptions.PloneAPIError`.
Each one carries `status_code`, `error_type`, `message`, `method`, `url` and the response `body`.

| Status | Exception |
|---|---|
| 400 | {class}`~plone_client.exceptions.PloneBadRequestError` |
| 401 | {class}`~plone_client.exceptions.PloneAuthenticationError` |
| 403 | {class}`~plone_client.exceptions.PloneForbiddenError`, also raised for locked items |
| 404 | {class}`~plone_client.exceptions.PloneNotFoundError` |
| 409 | {class}`~plone_client.exceptions.PloneConflictError` |
| 5xx | {class}`~plone_client.exceptions.PloneServerError` |

A site that cannot be reached raises {class}`~plone_client.exceptions.PloneConnectionError`, or its subclass {class}`~plone_client.exceptions.PloneTimeoutError`.

## Call other services

Add-ons often register their own services.
`get`, `post`, `patch`, `put` and `delete` take a path and return the decoded JSON body.

```python
client.get("/@my-addon-service", query="value")
client.post("/folder/@my-action", {"key": "value"})
```

{meth}`~plone_client.PloneClient.request` returns the {class}`httpx.Response` itself, and {meth}`~plone_client.PloneClient.iter_items` goes through the pages of any batched service.
