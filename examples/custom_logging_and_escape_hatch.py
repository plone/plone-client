"""
examples/custom_logging_and_escape_hatch.py
============================================
Shows how to:
1. Route plone-client log output through your own application logger
2. Use the escape hatch for custom add-on endpoints
3. Handle errors gracefully

Run:
    python examples/custom_logging_and_escape_hatch.py
"""

from __future__ import annotations

from plone_client import PloneClient
from plone_client import PloneClientError
from plone_client import PloneNotFoundError
from plone_client.logging_config import set_logger

import logging
import sys


# ── 1. Plug in your application's logger ─────────────────────────────────

app_logger = logging.getLogger("myapp")
app_logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s  %(message)s"))
app_logger.addHandler(handler)

# All plone-client log output now flows through myapp logger
set_logger(app_logger.getChild("plone"))


# ── 2. Custom retry configuration ────────────────────────────────────────

from plone_client import PloneClientConfig


cfg = PloneClientConfig(
    base_url="http://localhost:8080/Plone",
    username="admin",
    password="admin",
    max_retries=5,
    retry_backoff=1.0,  # sleep = 1.0 * 2^attempt → 1s, 2s, 4s, 8s, 16s
    timeout=60.0,
    log_level="DEBUG",
)


def main() -> None:
    with PloneClient(config=cfg) as client:
        # ── 3. Escape hatch: call a custom add-on endpoint ────────────
        #
        # Suppose you have an add-on that exposes /@my-custom-search
        try:
            response = client.request(
                "GET",
                "/@my-custom-search",
                params={"q": "plone", "category": "news"},
            )
            if response.status_code == 200:
                data = response.json()
                print(f"Custom search results: {data}")
            else:
                print(f"Unexpected status: {response.status_code}")

        except PloneNotFoundError:
            print("@my-custom-search endpoint not installed — skipping")

        # ── 4. POST to a custom service with JSON payload ─────────────
        try:
            response = client.post(
                "/@my-addon-action",
                json={"action": "reindex", "scope": "news"},
            )
            print(f"Custom action response: {response.json()}")
        except PloneNotFoundError:
            print("@my-addon-action not installed — skipping")

        # ── 5. Structured error handling ──────────────────────────────
        from plone_client import PloneAuthenticationError
        from plone_client import PloneForbiddenError
        from plone_client import PloneServerError

        paths_to_check = ["/front-page", "/does-not-exist", "/secret-area"]
        for path in paths_to_check:
            try:
                obj = client.content.get(path)
                print(f"OK  {path}: {obj.get('title', '?')}")
            except PloneNotFoundError:
                print(f"404 {path}: not found")
            except PloneForbiddenError:
                print(f"403 {path}: forbidden")
            except PloneAuthenticationError:
                print(f"401 {path}: not authenticated")
            except PloneServerError as exc:
                print(f"5xx {path}: server error — {exc}")
            except PloneClientError as exc:
                print(f"ERR {path}: {exc}")

        # ── 6. Renew token before it expires ──────────────────────────
        try:
            client.renew_token()
            print(f"Token renewed: {client.token[:20]}…")
        except PloneClientError as exc:
            print(f"Token renewal failed: {exc}")


if __name__ == "__main__":
    main()
