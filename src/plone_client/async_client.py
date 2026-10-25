"""
Async client for Plone sites via plone.restapi.

:class:`AsyncPloneClient` mirrors the synchronous :class:`~plone_client.PloneClient`
API exactly, but uses ``httpx.AsyncClient`` under the hood so it can be
``await``-ed inside ``asyncio`` / ``trio`` applications.

Extra dependency
----------------
Install with the ``async`` extra::

    pip install plone-client[async]

That pulls in ``httpx>=0.27``.

Usage
-----
::

    import asyncio
    from plone_client.async_client import AsyncPloneClient

    async def main():
        async with AsyncPloneClient(
            base_url="https://my.plone.site",
            username="admin",
            password="secret",
        ) as client:
            doc = await client.content.get("/front-page")
            results = await client.search.search({"portal_type": "Document"})

    asyncio.run(main())
"""

from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import httpx

import contextlib

from .config import PloneClientConfig
from .exceptions import PloneAPIError
from .exceptions import PloneAuthenticationError
from .exceptions import PloneClientError
from .exceptions import PloneConflictError
from .exceptions import PloneConnectionError
from .exceptions import PloneForbiddenError
from .exceptions import PloneNotFoundError
from .exceptions import PloneServerError
from .exceptions import PloneTimeoutError
from .logging_config import setup_logging


_RETRYABLE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "DELETE"})
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def _require_httpx() -> Any:
    """Import httpx or raise a friendly error."""
    try:
        import httpx

        return httpx
    except ImportError as exc:
        raise ImportError(
            "AsyncPloneClient requires httpx. "
            "Install it with: pip install plone-client[async]"
        ) from exc


class _AsyncConnection:
    """Internal async HTTP layer (mirrors PloneConnection)."""

    def __init__(self, config: PloneClientConfig) -> None:
        httpx = _require_httpx()
        self._config = config
        self._token: str = config.token
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            verify=config.verify_ssl,
            timeout=config.timeout,
        )

    async def login(self) -> None:
        if not self._config.has_credentials:
            raise PloneClientError("Cannot login: no username/password configured.")
        response = await self._request(
            "POST",
            "/@login",
            json={"login": self._config.username, "password": self._config.password},
            _authenticate=False,
        )
        data = response.json()
        self._token = data.get("token", "")
        if not self._token:
            raise PloneAuthenticationError("Login succeeded but no token was returned.")
        self._client.headers["Authorization"] = f"Bearer {self._token}"

    async def logout(self) -> None:
        if self._token:
            with contextlib.suppress(PloneClientError):
                await self._request("POST", "/@logout")
        self._token = ""
        self._client.headers.pop("Authorization", None)

    async def renew_token(self) -> None:
        response = await self._request("POST", "/@login-renew")
        data = response.json()
        new_token = data.get("token", "")
        if new_token:
            self._token = new_token
            self._client.headers["Authorization"] = f"Bearer {new_token}"

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request(method, path, **kwargs)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        _authenticate: bool = True,
        **kwargs: Any,
    ) -> Any:
        httpx = _require_httpx()
        if _authenticate and self._token:
            self._client.headers["Authorization"] = f"Bearer {self._token}"

        url = path
        last_exc: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            if attempt:
                import asyncio

                sleep_time = self._config.retry_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(sleep_time)

            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
            except httpx.ConnectError as exc:
                last_exc = exc
                continue
            except httpx.RequestError as exc:
                raise PloneConnectionError(str(exc)) from exc

            if (
                response.status_code in _RETRYABLE_STATUSES
                and method.upper() in _RETRYABLE_METHODS
                and attempt < self._config.max_retries
            ):
                last_exc = None
                continue

            return _raise_for_status(response)

        if last_exc is not None:
            httpx2 = _require_httpx()
            if isinstance(last_exc, httpx2.TimeoutException):
                raise PloneTimeoutError("Request timed out.") from last_exc
        raise PloneConnectionError(str(last_exc)) from last_exc

    @property
    def token(self) -> str:
        return self._token

    async def aclose(self) -> None:
        await self._client.aclose()


def _raise_for_status(response: Any) -> Any:
    status = response.status_code
    if status < 400:
        return response
    try:
        body: Any = response.json()
    except Exception:
        body = response.text
    message = (
        body.get("message", response.reason_phrase)
        if isinstance(body, dict)
        else str(body)
    )
    mapping = {
        401: PloneAuthenticationError,
        403: PloneForbiddenError,
        404: PloneNotFoundError,
        409: PloneConflictError,
    }
    exc_class = mapping.get(status)
    if exc_class:
        raise exc_class(message)
    if status >= 500:
        raise PloneServerError(f"Server error {status}: {message}")
    raise PloneAPIError(message, status_code=status, response_body=body)


# ---------------------------------------------------------------------------
# Async managers
# ---------------------------------------------------------------------------


class _AsyncBaseManager:
    def __init__(self, conn: _AsyncConnection) -> None:
        self._conn = conn

    async def _get(self, path: str, **kwargs: Any) -> Any:
        r = await self._conn.request("GET", path, **kwargs)
        return r.json()

    async def _post(self, path: str, **kwargs: Any) -> Any:
        r = await self._conn.request("POST", path, **kwargs)
        return r.json()

    async def _patch(self, path: str, **kwargs: Any) -> Any:
        r = await self._conn.request("PATCH", path, **kwargs)
        return r.json()

    async def _put(self, path: str, **kwargs: Any) -> Any:
        r = await self._conn.request("PUT", path, **kwargs)
        return r.json()

    async def _delete(self, path: str, **kwargs: Any) -> None:
        await self._conn.request("DELETE", path, **kwargs)


class AsyncContentManager(_AsyncBaseManager):
    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        return await self._get(path, params=params or None)

    async def create(
        self, container: str, type_: str, title: str, **fields: Any
    ) -> dict[str, Any]:
        return await self._post(
            container, json={"@type": type_, "title": title, **fields}
        )

    async def update(self, path: str, **fields: Any) -> dict[str, Any]:
        return await self._patch(path, json=fields)

    async def delete(self, path: str) -> None:
        await self._delete(path)

    async def copy(self, source: str, target: str) -> dict[str, Any]:
        return await self._post(f"{source}/@copy", json={"target": target})

    async def move(self, source: str, target: str) -> dict[str, Any]:
        return await self._post(f"{source}/@move", json={"target": target})

    async def transition(
        self, path: str, transition_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        return await self._post(f"{path}/@workflow/{transition_id}", json=kwargs)

    async def navigation(self, path: str = "/", depth: int = 1) -> dict[str, Any]:
        return await self._get(f"{path}/@navigation", params={"depth": depth})

    async def breadcrumbs(self, path: str) -> dict[str, Any]:
        return await self._get(f"{path}/@breadcrumbs")


class AsyncSearchManager(_AsyncBaseManager):
    async def search(
        self, query: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        params: dict[str, Any] = {**(query or {}), **kwargs}
        return await self._get("/@search", params=params)

    async def querystring(
        self, query: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        return await self._post("/@querystring-search", json={"query": query, **kwargs})

    async def iterate(
        self, query: dict[str, Any] | None = None, b_size: int = 50, **kw: Any
    ):
        """Async generator that lazily pages through all search results."""
        b_start = 0
        while True:
            result = await self.search(query, b_size=b_size, b_start=b_start, **kw)
            items = result.get("items", [])
            for item in items:
                yield item
            total = result.get("items_total", 0)
            b_start += b_size
            if b_start >= total:
                break


class AsyncUsersManager(_AsyncBaseManager):
    async def list(self, query: str = "") -> list[dict[str, Any]]:
        params = {"query": query} if query else None
        return await self._get("/@users", params=params)

    async def get(self, user_id: str) -> dict[str, Any]:
        return await self._get(f"/@users/{user_id}")

    async def create(self, username: str, email: str, **fields: Any) -> dict[str, Any]:
        return await self._post(
            "/@users", json={"username": username, "email": email, **fields}
        )

    async def update(self, user_id: str, **fields: Any) -> dict[str, Any]:
        return await self._patch(f"/@users/{user_id}", json=fields)

    async def delete(self, user_id: str) -> None:
        await self._delete(f"/@users/{user_id}")

    async def my_information(self) -> dict[str, Any]:
        return await self._get("/@my-information")


class AsyncGroupsManager(_AsyncBaseManager):
    async def list(self, query: str = "") -> list[dict[str, Any]]:
        params = {"query": query} if query else None
        return await self._get("/@groups", params=params)

    async def get(self, group_id: str) -> dict[str, Any]:
        return await self._get(f"/@groups/{group_id}")

    async def create(self, groupname: str, **fields: Any) -> dict[str, Any]:
        return await self._post("/@groups", json={"groupname": groupname, **fields})

    async def update(self, group_id: str, **fields: Any) -> dict[str, Any]:
        return await self._patch(f"/@groups/{group_id}", json=fields)

    async def delete(self, group_id: str) -> None:
        await self._delete(f"/@groups/{group_id}")

    async def add_member(self, group_id: str, user_id: str) -> dict[str, Any]:
        return await self._post(f"/@groups/{group_id}/members/{user_id}")

    async def remove_member(self, group_id: str, user_id: str) -> None:
        await self._delete(f"/@groups/{group_id}/members/{user_id}")


class AsyncSharingManager(_AsyncBaseManager):
    async def get(self, path: str) -> dict[str, Any]:
        return await self._get(f"{path}/@sharing")

    async def update(
        self, path: str, entries: list[dict[str, Any]], inherit: bool | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"entries": entries}
        if inherit is not None:
            payload["inherit"] = inherit
        return await self._post(f"{path}/@sharing", json=payload)


class AsyncSiteManager(_AsyncBaseManager):
    async def info(self) -> dict[str, Any]:
        return await self._get("/")

    async def types(self) -> dict[str, Any]:
        return await self._get("/@types")

    async def vocabulary(self, vocab_id: str, query: str = "") -> dict[str, Any]:
        params = {"query": query} if query else None
        return await self._get(f"/@vocabularies/{vocab_id}", params=params)

    async def roles(self) -> list[str]:
        return await self._get("/@roles")


class AsyncRegistryManager(_AsyncBaseManager):
    async def get(self, key: str | None = None) -> dict[str, Any]:
        path = f"/@registry/{key}" if key else "/@registry"
        return await self._get(path)

    async def set(self, key: str, value: Any) -> None:
        await self._patch(f"/@registry/{key}", json={"value": value})


class AsyncFilesManager(_AsyncBaseManager):
    async def download(self, path: str, field: str = "file") -> bytes:
        r = await self._conn.request("GET", f"{path}/@download/{field}")
        return r.content

    async def image_scales(self, path: str) -> dict[str, Any]:
        return await self._get(f"{path}/@images")

    async def image_scale(self, path: str, field: str, scale: str) -> dict[str, Any]:
        return await self._get(f"{path}/@images/{field}/{scale}")


class AsyncCommentsManager(_AsyncBaseManager):
    async def list(self, path: str) -> dict[str, Any]:
        return await self._get(f"{path}/@comments")

    async def add(self, path: str, text: str) -> dict[str, Any]:
        return await self._post(f"{path}/@comments", json={"text": text})

    async def delete(self, path: str, comment_id: str) -> None:
        await self._delete(f"{path}/@comments/{comment_id}")


class AsyncHistoryManager(_AsyncBaseManager):
    async def list(self, path: str) -> list[dict[str, Any]]:
        return await self._get(f"{path}/@history")

    async def revert(self, path: str, version: int) -> dict[str, Any]:
        return await self._patch(f"{path}/@history", json={"version": version})


class AsyncRelationsManager(_AsyncBaseManager):
    async def list(self, relation: str | None = None, **params: Any) -> dict[str, Any]:
        p: dict[str, Any] = {}
        if relation:
            p["relation"] = relation
        p.update(params)
        return await self._get("/@relations", params=p or None)

    async def create(
        self, source: str, target: str, relation: str = "relatedItems"
    ) -> dict[str, Any]:
        return await self._post(
            "/@relations",
            json={"source": source, "target": target, "relation": relation},
        )

    async def broken(self) -> dict[str, Any]:
        return await self._get("/@brokenrelations")


class AsyncWorkingCopyManager(_AsyncBaseManager):
    async def checkout(self, path: str) -> dict[str, Any]:
        return await self._post(f"{path}/@workingcopy")

    async def checkin(self, path: str, message: str = "") -> dict[str, Any]:
        return await self._patch(
            f"{path}/@workingcopy", json={"checkin_message": message}
        )

    async def cancel(self, path: str) -> None:
        await self._delete(f"{path}/@workingcopy")


class AsyncBlocksManager(_AsyncBaseManager):
    async def get_slots(self, path: str) -> dict[str, Any]:
        return await self._get(f"{path}/@slots")

    async def create_slot(
        self,
        path: str,
        slot_name: str,
        blocks: dict[str, Any],
        blocks_layout: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "blocks": blocks,
            "blocks_layout": blocks_layout or {"items": list(blocks.keys())},
        }
        return await self._post(f"{path}/@slots/{slot_name}", json=payload)

    async def delete_slot(self, path: str, slot_name: str) -> None:
        await self._delete(f"{path}/@slots/{slot_name}")


class AsyncDatabaseManager(_AsyncBaseManager):
    async def info(self) -> dict[str, Any]:
        return await self._get("/@database")

    async def reindex(self) -> dict[str, Any]:
        return await self._post("/@reindex")


class AsyncUtilitiesManager(_AsyncBaseManager):
    async def resolve_uid(self, uid: str) -> dict[str, Any]:
        return await self._get(f"/@resolveuid/{uid}")

    async def ids(self, path: str) -> list[str]:
        result = await self._get(f"{path}/@ids")
        return result if isinstance(result, list) else result.get("items", [])

    async def search_principals(self, query: str, path: str = "/") -> dict[str, Any]:
        return await self._get(f"{path}/@principals", params={"search": query})

    async def site_config(self) -> dict[str, Any]:
        return await self._get("/@config")


# ---------------------------------------------------------------------------
# AsyncPloneClient
# ---------------------------------------------------------------------------


class AsyncPloneClient:
    """
    Async counterpart of :class:`~plone_client.PloneClient`.

    Uses ``httpx.AsyncClient`` for non-blocking I/O.  Every sync manager
    has an async equivalent accessible as the same attribute name:

    ``content``, ``search``, ``users``, ``groups``, ``sharing``,
    ``site``, ``registry``, ``files``, ``comments``, ``history``,
    ``relations``, ``working_copy``, ``blocks``, ``database``, ``utilities``

    Example::

        async with AsyncPloneClient(
            "https://site", username="admin", password="x"
        ) as c:
            doc = await c.content.get("/front-page")
            async for item in c.search.iterate({"portal_type": "Document"}):
                print(item["@id"])
            # Concurrent fetches
            import asyncio
            pages = await asyncio.gather(
                c.content.get("/news"),
                c.content.get("/events"),
            )
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        username: str = "",
        password: str = "",
        token: str = "",
        config: PloneClientConfig | None = None,
        **config_kwargs: Any,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = PloneClientConfig(
                base_url=base_url or config_kwargs.pop("base_url", ""),
                username=username or config_kwargs.pop("username", ""),
                password=password or config_kwargs.pop("password", ""),
                token=token or config_kwargs.pop("token", ""),
                **config_kwargs,
            )

        setup_logging(level=self._config.log_level)
        self._conn = _AsyncConnection(self._config)
        self._init_managers()

    def _init_managers(self) -> None:
        self.content = AsyncContentManager(self._conn)
        self.search = AsyncSearchManager(self._conn)
        self.users = AsyncUsersManager(self._conn)
        self.groups = AsyncGroupsManager(self._conn)
        self.sharing = AsyncSharingManager(self._conn)
        self.site = AsyncSiteManager(self._conn)
        self.registry = AsyncRegistryManager(self._conn)
        self.files = AsyncFilesManager(self._conn)
        self.comments = AsyncCommentsManager(self._conn)
        self.history = AsyncHistoryManager(self._conn)
        self.relations = AsyncRelationsManager(self._conn)
        self.working_copy = AsyncWorkingCopyManager(self._conn)
        self.blocks = AsyncBlocksManager(self._conn)
        self.database = AsyncDatabaseManager(self._conn)
        self.utilities = AsyncUtilitiesManager(self._conn)

    async def open(self) -> None:
        if not self._config.has_token and self._config.has_credentials:
            await self._conn.login()

    async def close(self) -> None:
        if not self._config.has_token:
            await self._conn.logout()
        await self._conn.aclose()

    async def __aenter__(self) -> AsyncPloneClient:
        await self.open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Raw async escape hatch — mirrors :meth:`PloneClient.request`."""
        return await self._conn.request(method.upper(), path, **kwargs)

    @property
    def token(self) -> str:
        return self._conn.token

    @property
    def config(self) -> PloneClientConfig:
        return self._config

    def __repr__(self) -> str:  # pragma: no cover
        return f"AsyncPloneClient(base_url={self._config.base_url!r})"
