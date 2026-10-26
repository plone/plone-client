---
myst:
  html_meta:
    "description": "Call plone.restapi services and add-on services that plone-client has no manager or command for."
    "property=og:description": "Call plone.restapi services and add-on services that plone-client has no manager or command for."
    "property=og:title": "Call other services"
---

(howto-call-other-services)=

# Call other services

This guide shows you how to call a service that plone-client has no manager or command for, such as one an add-on registers.
These calls still get the client's authentication, retries, errors, and safety switches.

## From Python

`get`, `post`, `patch`, `put`, and `delete` take a path and return the decoded JSON body.

```python
client.get("/@my-addon-service", query="value")
client.post("/news/hello/@my-action", {"key": "value"})
client.patch("/news/hello", {"title": "Hello"})
```

The path can include the item, as in `/news/hello/@my-action`, or be a full URL inside the site.

To read headers or the status, call {meth}`~plone_client.PloneClient.request`, which returns the `httpx.Response` itself.

```python
response = client.request("GET", "/@my-addon-service")
print(response.status_code, response.headers["content-type"])
```

To go through every page of a batched service, use {meth}`~plone_client.PloneClient.iter_items`.

```python
for entry in client.iter_items("/@my-addon-listing", {"b_size": 100}):
    print(entry["@id"])
```

## From the command line

`request` sends any request.

```shell
plone-client request GET /@my-addon-service -P query=value
plone-client request POST /news/hello/@my-action -d '{"key": "value"}'
plone-client request PATCH /news/hello -d @changes.json -H "Lock-Token: 0.1234"
```

`-P` adds a query parameter, `-d` sends a JSON body, and `-H` adds a header; each one is repeatable.

## Related

- {ref}`reference-managers` lists the services that already have a manager.
- {ref}`reference-client` documents the request methods.
