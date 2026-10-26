# Sync content from an external source

This guide shows how to keep a Plone folder in step with records that live elsewhere: a JSON feed, a spreadsheet, another CMS, or a database.
The complete script is in `examples/sync_json.py`.

## Choose a key

A sync needs to know which page belongs to which record.
The simplest key is the item's id, the last segment of its URL.
Derive it from a stable identifier of the record, never from a title that may change.

When the id cannot be stable, keep the record's identifier in a field of the page, and look pages up with a catalog query on that field instead.

## Read what is already there

List the folder once, before going through the records, rather than asking the site about each record.

```python
existing = {
    entry["@id"].rsplit("/", 1)[-1]: entry
    for entry in client.content.children(folder, portal_type="Document")
}
```

{meth}`~plone_client.managers.content.ContentManager.children` returns catalog entries, fetched a page at a time, so this stays cheap for large folders.

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

Updating only the pages that changed keeps the site's modification dates and version history meaningful.
`representation=False` skips sending the changed page back, which the sync does not need.

Whatever is left in `existing` after the loop has no record any more.
Deleting it is a choice the script should make explicit, which is why `examples/sync_json.py` deletes only with `--prune`.

## Plan before changing

Make the script report what it would do unless it is told to apply the changes.
A client created with `dry_run=True` reads from the site as usual but records each change in `client.dry_run_log` instead of sending it.

```python
client = PloneClient.from_env(dry_run=not args.apply)
```

In a dry run, a create returns a description of the request it skipped, not the new item.
Code that goes on to use the new item's `@id`, to publish it or to add content inside it, must stop at that point in a dry run.

## Run it from a scheduler

A sync run by cron or CI has no one to type a password.
Give it the settings through the environment, `PLONE_CLIENT_URL`, `PLONE_CLIENT_USERNAME` and `PLONE_CLIENT_PASSWORD`, and use {meth}`~plone_client.PloneClient.from_env`.
On a workstation, a profile keeps the password in the keyring instead; see {doc}`profiles`.

Requests that fail because of a dropped connection or an overloaded site, with status 429, 502, 503 or 504, are retried with an increasing delay.
Retries apply only to requests that are safe to repeat, so a create is never sent twice.
Tune them with the `retries` and `backoff` arguments.
