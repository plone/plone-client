---
myst:
  html_meta:
    "description": "Keep a Plone folder in step with records from an external source, such as a JSON feed or another system."
    "property=og:description": "Keep a Plone folder in step with records from an external source, such as a JSON feed or another system."
    "property=og:title": "Sync content from an external source"
---

(howto-sync)=

# Sync content from an external source

This guide shows you how to keep a Plone folder in step with records that live elsewhere: a JSON feed, a spreadsheet, another CMS, or a database.
Each run creates the pages for new records, updates the pages whose records changed, and optionally deletes the pages whose records are gone.

## Choose a key

A sync must know which page belongs to which record.
Use the item's id, the last segment of its URL, and derive it from a stable identifier of the record, never from a title that may change.

If the id cannot be stable, store the record's identifier in a field of the page, and find pages with a catalog query on that field instead.

## Read the folder once

List the folder before going through the records, instead of asking the site about each record.

```python
existing = {
    entry["@id"].rsplit("/", 1)[-1]: entry
    for entry in client.content.children(folder, portal_type="Document")
}
```

{meth}`~plone_client.managers.content.ContentManager.children` returns catalog entries a page at a time, so this stays cheap for large folders.

## Create, update, and delete

```python
for record in records:
    entry = existing.pop(record["id"], None)
    if entry is None:
        client.content.create(folder, "Document", id=record["id"], **page_data(record))
    elif changed(client.content.get(entry["@id"], include_items=False), record):
        client.content.update(entry["@id"], page_data(record), representation=False)

for entry in existing.values():
    client.content.delete(entry["@id"])
```

Update only the pages that changed, so their modification dates and version history stay meaningful.
`representation=False` skips sending the changed page back, which a sync does not need.

Whatever is left in `existing` after the loop has no record any more.
Make deleting it an explicit choice of whoever runs the sync.

## Plan before changing

Make the script report what it would do, unless told to apply the changes.
A client created with `dry_run=True` reads the site as usual but records each change instead of sending it.

```python
client = PloneClient.from_env(dry_run=not args.apply)
```

In a dry run, a create returns a description of the request it skipped, not the new item.
Stop before any step that needs the new item's `@id`.

## Run it on a schedule

A sync run by cron or CI has nobody to type a password.
Give it the settings through the environment and use {meth}`~plone_client.PloneClient.from_env`.

Requests that fail because of a dropped connection or an overloaded site are retried.
A create is never retried, so it never runs twice.

## The complete script

The script reads records from a JSON file.
Without `--apply` it only reports what it would do, and it deletes pages only with `--prune`.

```shell
python sync_json.py records.json /news/releases
python sync_json.py records.json /news/releases --apply --prune
```

```{literalinclude} ../_examples/sync_json.py
:language: python
```

## Related

- {ref}`howto-preview-changes` covers `dry_run` and `read_only`.
- {ref}`reference-client` describes the retries.
