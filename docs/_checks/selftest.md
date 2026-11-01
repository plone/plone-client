# Self-test of the page runner

This page exercises every mark of `run.py` against the seeded site.

<!-- check: start -->

<!-- check: stdin admin -->
```shell
plone-client profile add selftest --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --use
```

<!-- check: contains -->
```shell
plone-client info
```

```text
"authenticated": true
```

The seed created five news items.

```shell
plone-client ls /news -f id,review_state -c | python3 -c 'import json, sys; print(len(json.load(sys.stdin)))'
```

```text
5
```

The sample user exists, and the shell keeps its variables between blocks.

```shell
export WHO=jdoe
```

```shell
plone-client users get "$WHO" -f id,fullname
```

```json
{
  "id": "jdoe",
  "fullname": "Jo Doe"
}
```

<!-- check: file script.py -->
```python
from plone_client import PloneClient

with PloneClient(
    "http://localhost:8080/Plone", username="admin", password="admin"
) as site:
    print(site.search.count(portal_type="News Item"))
```

```shell
python script.py
```

```text
5
```

A refused change exits with its own code.

<!-- check: exit 7 -->
```shell
plone-client --read-only delete /news --yes
```

<!-- check: skip -->
```shell
this-command-does-not-exist
```

<!-- check: stop -->
