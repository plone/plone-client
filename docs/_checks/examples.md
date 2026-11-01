# Run the example scripts

The how-to guides include these scripts with `literalinclude`, so this page runs them.

<!-- check: start -->

```shell
cp "$(python -c 'import seed, pathlib; print(pathlib.Path(seed.__file__).parent)')"/examples/*.py .
export PLONE_CLIENT_URL=http://localhost:8080/Plone
export PLONE_CLIENT_USERNAME=admin
export PLONE_CLIENT_PASSWORD=admin
```

<!-- check: file records.json -->
```json
[
  {"id": "one", "title": "One", "description": "First", "text": "One.", "subjects": ["release"]},
  {"id": "two", "title": "Two", "description": "Second", "text": "Two.", "subjects": []}
]
```

Without `--apply`, nothing changes.

```shell
python sync_json.py records.json /news
```

```text
+ one
+ two
2 created, 0 updated, 0 deleted, 0 unchanged (dry run: nothing was changed)
```

```shell
python sync_json.py records.json /news --apply
```

```text
+ one
+ two
2 created, 0 updated, 0 deleted, 0 unchanged
```

A second run finds nothing to do.

```shell
python sync_json.py records.json /news --apply
```

```text
0 created, 0 updated, 0 deleted, 2 unchanged
```

A changed record updates its page, and `--prune` deletes the page whose record is gone.

```shell
python -c "
import json, pathlib
path = pathlib.Path('records.json')
records = json.loads(path.read_text())[:1]
records[0]['title'] = 'Uno'
path.write_text(json.dumps(records))
"
python sync_json.py records.json /news --apply --prune
```

```text
~ one
- two
0 created, 1 updated, 1 deleted, 0 unchanged
```

<!-- check: file news.txt -->
```text
Plone 6.2 is out
The release brings a new distribution.

Plone 6.2 is out.

It took a while.
```

<!-- check: contains -->
```shell
python -c "
import pathlib, seed
pathlib.Path('lead.png').write_bytes(seed.png(200, 30, 30))
"
python publish_news.py news.txt /news --image lead.png
```

```text
Dry run: nothing was changed
```

```shell
python publish_news.py news.txt /news --image lead.png --apply
```

```text
Published http://localhost:8080/Plone/news/plone-6-2-is-out
```

```shell
plone-client get /news/plone-6-2-is-out -f title,review_state
```

```json
{
  "title": "Plone 6.2 is out",
  "review_state": "published"
}
```

<!-- check: stop -->
