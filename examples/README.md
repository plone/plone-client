# Examples

Scripts that use plone-client as a library.
Both only report what they would do unless given `--apply`.

`sync_json.py`
: Keeps a folder in step with records from a JSON file: creates, updates, and with `--prune` deletes pages.

`publish_news.py`
: Publishes a news item from a text file, with a lead image.

They connect with the `PLONE_CLIENT_*` environment variables, or with a profile passed as `--profile`.

```shell
export PLONE_CLIENT_URL=http://localhost:8080/Plone
export PLONE_CLIENT_USERNAME=admin
export PLONE_CLIENT_PASSWORD=admin

uv run python examples/sync_json.py records.json /news/releases
uv run python examples/sync_json.py records.json /news/releases --apply
uv run python examples/publish_news.py news.txt /news --image lead.jpg --apply
```
