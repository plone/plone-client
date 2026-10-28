"""The :class:`PloneClient`: one site, one HTTP session, every service.

Example::

    from plone_client import PloneClient

    with PloneClient("https://example.org", username="admin", password="pw") as site:
        page = site.content.get("/about")
        for item in site.search.iter(portal_type="News Item", review_state="published"):
            print(item["@id"])
"""

from .auth import AuthMethod
from .auth import build_auth
from .auth import JWTAuth
from .auth import TokenAuth
from .exceptions import error_from_response
from .exceptions import PloneConfigurationError
from .exceptions import PloneConnectionError
from .exceptions import PloneReadOnlyError
from .exceptions import PloneTimeoutError
from .managers import AddonsManager
from .managers import AliasesManager
from .managers import BlockTypesManager
from .managers import CommentsManager
from .managers import ContentManager
from .managers import ContentRulesManager
from .managers import ControlpanelsManager
from .managers import FilesManager
from .managers import GroupsManager
from .managers import HistoryManager
from .managers import NavigationManager
from .managers import QuerystringManager
from .managers import RegistryManager
from .managers import RelationsManager
from .managers import SearchManager
from .managers import SharingManager
from .managers import SystemManager
from .managers import TranslationsManager
from .managers import TypesManager
from .managers import UsersManager
from .managers import VocabulariesManager
from .managers import WorkflowManager
from .managers import WorkingCopyManager
from collections.abc import Iterator
from collections.abc import Mapping
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from pathlib import Path
from typing import Any
from typing import Self
from urllib.parse import parse_qsl
from urllib.parse import urlsplit

import httpx
import logging
import os
import ssl
import time


logger = logging.getLogger("plone_client")

try:
    _VERSION = version("plone-client")
except PackageNotFoundError:  # no cov
    _VERSION = "unknown"

USER_AGENT = f"plone-client/{_VERSION}"

#: Methods that never change the site.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
#: Methods that may be repeated without changing the outcome.
IDEMPOTENT_METHODS = SAFE_METHODS | {"PUT", "DELETE"}
#: Statuses worth retrying for idempotent methods.
RETRY_STATUSES = frozenset({429, 502, 503, 504})
#: Services that answer a ``POST`` without changing the site.
READ_ONLY_POSTS = ("@querystring-search", "@login", "@login-renew")

Params = Mapping[str, Any] | list[tuple[str, Any]] | None
QueryPairs = list[tuple[str, str | int | float | bool | None]]


def encode_params(params: Params) -> QueryPairs:
    """Encode query parameters the way ``plone.restapi`` reads them.

    * ``None`` values are dropped;
    * booleans become ``true`` / ``false``;
    * lists and tuples become repeated keys
      (``portal_type=Document&portal_type=News Item``);
    * nested mappings are flattened with dots, which is how catalog query
      options are written (``{"path": {"query": "/news", "depth": 1}}``
      becomes ``path.query=/news&path.depth=1``).

    :param params: Parameters as a mapping or as a list of pairs.
    :returns: Encoded key/value pairs.
    """
    if not params:
        return []
    pairs = params.items() if isinstance(params, Mapping) else params
    encoded: QueryPairs = []
    for key, value in pairs:
        if value is None:
            continue
        if isinstance(value, Mapping):
            encoded.extend(
                encode_params([(f"{key}.{sub}", val) for sub, val in value.items()])
            )
        elif isinstance(value, list | tuple | set | frozenset):
            encoded.extend((key, _scalar(item)) for item in value)
        else:
            encoded.append((key, _scalar(value)))
    return encoded


def _scalar(value: Any) -> str:
    """Encode one query parameter value.

    :param value: The value.
    :returns: Its string form.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def ssl_verify(verify: bool | str | ssl.SSLContext) -> bool | ssl.SSLContext:
    """TLS verification setting for :mod:`httpx`.

    :param verify: ``True``, ``False``, an SSL context, or the path of a CA
        bundle (a file or a directory of certificates).
    :returns: The boolean or context; a path becomes a context that trusts
        only the certificates of that bundle.
    :raises PloneConfigurationError: If the path does not exist.
    """
    if not isinstance(verify, str):
        return verify
    path = Path(verify).expanduser()
    if path.is_dir():
        return ssl.create_default_context(capath=str(path))
    if path.is_file():
        return ssl.create_default_context(cafile=str(path))
    raise PloneConfigurationError(f"CA bundle not found: {path}")


def _parse_retry_after(response: httpx.Response) -> float:
    """Seconds to wait according to ``Retry-After``.

    :param response: The response.
    :returns: Seconds, or ``0.0`` when the header is missing or is a date.
    """
    try:
        return max(0.0, float(response.headers.get("Retry-After", "")))
    except ValueError:
        return 0.0


class PloneClient:
    """Client for one Plone site, through ``plone.restapi``.

    Paths given to the client and its managers can be written as site paths
    (``/news/item``), as absolute URLs of the site (the ``@id`` values the
    API returns) or as API URLs (with ``++api++``). They are all mapped to
    the same API URL.

    :param url: URL of the site root, such as ``https://example.org`` or
        ``http://localhost:8080/Plone``.
    :param username: Login name.
    :param password: Password.
    :param token: JWT issued beforehand; used instead of the username and
        password.
    :param auth_method: ``basic`` (default) sends the username and password
        on every request; ``jwt`` logs in with ``@login`` and sends the token.
    :param auth: Any :class:`httpx.Auth`; overrides the credentials above.
    :param api_prefix: Traversal prefix of the REST API. ``++api++`` works
        with and without a Volto frontend in front of the backend; use an
        empty string to rely on the ``Accept`` header only.
    :param timeout: Seconds to wait for the site.
    :param verify: Verify TLS certificates. A path (a file or a directory)
        verifies them against that CA bundle instead of the default one; an
        :class:`ssl.SSLContext` is used as given.
    :param retries: Times a request is repeated after a network error, or
        after a ``429``/``502``/``503``/``504`` answer to an idempotent method.
    :param backoff: Base delay in seconds between retries; doubles each time.
    :param headers: Extra headers sent with every request.
    :param read_only: Refuse every request that could change the site.
    :param dry_run: Do not send requests that could change the site; log them
        and return a description of what would have been sent instead.
    :param frontend_url: URL of the Volto frontend, for services that Volto
        serves itself (``@blocks-schema``); the site URL by default, which is
        right when ``url`` is the frontend.
    :param transport: Custom :mod:`httpx` transport, mostly for tests.
    """

    def __init__(
        self,
        url: str,
        *,
        username: str = "",
        password: str = "",
        token: str = "",
        auth_method: AuthMethod = "basic",
        auth: httpx.Auth | None = None,
        api_prefix: str = "++api++",
        timeout: float = 30.0,
        verify: bool | str | ssl.SSLContext = True,
        retries: int = 3,
        backoff: float = 0.5,
        headers: Mapping[str, str] | None = None,
        read_only: bool = False,
        dry_run: bool = False,
        frontend_url: str = "",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not url:
            raise ValueError("The URL of the site is required")
        self.url = url.rstrip("/")
        self.frontend_url = frontend_url.rstrip("/") or self.url
        self.api_prefix = api_prefix.strip("/")
        self.retries = retries
        self.backoff = backoff
        self.read_only = read_only
        self.dry_run = dry_run
        #: Requests skipped because of ``dry_run``, oldest first.
        self.dry_run_log: list[dict[str, Any]] = []
        self._recordings: list[list[dict[str, Any]]] = []
        if auth is None:
            auth = build_auth(
                username=username,
                password=password,
                token=token,
                method=auth_method,
                login_url=self.api_url("/@login"),
            )
        self.username = username
        self._password = password
        self._token = token
        verify = ssl_verify(verify)
        self._http = httpx.Client(
            auth=auth,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                **(headers or {}),
            },
            timeout=timeout,
            verify=verify,
            transport=transport or httpx.HTTPTransport(retries=retries, verify=verify),
        )
        self.content = ContentManager(self)
        self.search = SearchManager(self)
        self.querystring = QuerystringManager(self)
        self.workflow = WorkflowManager(self)
        self.files = FilesManager(self)
        self.navigation = NavigationManager(self)
        self.aliases = AliasesManager(self)
        self.history = HistoryManager(self)
        self.comments = CommentsManager(self)
        self.translations = TranslationsManager(self)
        self.working_copy = WorkingCopyManager(self)
        self.relations = RelationsManager(self)
        self.users = UsersManager(self)
        self.groups = GroupsManager(self)
        self.sharing = SharingManager(self)
        self.types = TypesManager(self)
        self.block_types = BlockTypesManager(self)
        self.vocabularies = VocabulariesManager(self)
        self.registry = RegistryManager(self)
        self.controlpanels = ControlpanelsManager(self)
        self.addons = AddonsManager(self)
        self.content_rules = ContentRulesManager(self)
        self.system = SystemManager(self)

    # ------------------------------------------------------------------
    # Alternative constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, prefix: str = "PLONE_CLIENT_", **overrides: Any) -> Self:
        """Build a client from environment variables.

        Reads ``<prefix>URL``, ``<prefix>USERNAME``, ``<prefix>PASSWORD``,
        ``<prefix>TOKEN``, ``<prefix>AUTH_METHOD``, ``<prefix>TIMEOUT``,
        ``<prefix>VERIFY``, ``<prefix>RETRIES``, ``<prefix>BACKOFF``,
        ``<prefix>READ_ONLY`` and ``<prefix>FRONTEND_URL``; see
        :func:`~plone_client.profiles.settings_from_env`.

        :param prefix: Prefix of the variable names.
        :param overrides: Keyword arguments that win over the environment.
        :returns: A configured client.
        :raises PloneConfigurationError: If no URL is set.
        """
        from .profiles import settings_from_env

        settings = settings_from_env(os.environ, prefix=prefix)
        return cls(**{**settings, **overrides})

    @classmethod
    def from_profile(
        cls,
        name: str = "",
        *,
        config_file: Path | None = None,
        **overrides: Any,
    ) -> Self:
        """Build a client from a named profile.

        Profiles live in the configuration file (see :mod:`plone_client.profiles`)
        and their secrets in the operating system's keyring.

        :param name: Profile name; empty selects the current profile.
        :param config_file: Configuration file; defaults to the user's.
        :param overrides: Keyword arguments that win over the profile.
        :returns: A configured client.
        :raises PloneConfigurationError: If the profile or its secret is missing.
        """
        from .profiles import load_config

        config = load_config(config_file)
        profile = config.get(name or config.current_name())
        return cls(**{**profile.client_settings(), **overrides})

    # ------------------------------------------------------------------
    # URLs and paths
    # ------------------------------------------------------------------

    @property
    def api_root(self) -> str:
        """Absolute URL of the API root."""
        return f"{self.url}/{self.api_prefix}" if self.api_prefix else self.url

    @property
    def has_credentials(self) -> bool:
        """Whether the client was given a username or a token.

        Plone answers wrong credentials as an anonymous request, so this says
        whether an anonymous answer is a rejection (the command line's
        ``info`` and ``profile test`` report it).

        :returns: ``True`` if a username or a token is configured.
        """
        return bool(self.username or self._token)

    def path(self, ref: str) -> str:
        """Site path for a path or a URL of the site.

        :param ref: ``/news``, ``news``, ``https://example.org/news`` or
            ``https://example.org/++api++/news``. A query string is dropped.
        :returns: Path starting with ``/``, without a trailing slash
            (``/`` for the site root).
        :raises ValueError: If ``ref`` is a URL of another site.
        """
        ref = ref.strip()
        if "://" in ref:
            parts = urlsplit(ref)
            url = f"{parts.scheme}://{parts.netloc}{parts.path}"
            if url != self.url and not url.startswith(f"{self.url}/"):
                raise ValueError(f"{ref} is not a URL of {self.url}")
            ref = url[len(self.url) :]
        else:
            ref = ref.split("?", 1)[0]
        segments = [segment for segment in ref.split("/") if segment]
        if self.api_prefix and segments[:1] == [self.api_prefix]:
            segments = segments[1:]
        return "/" + "/".join(segments)

    def api_url(self, ref: str) -> str:
        """Absolute API URL for a path or a URL of the site.

        :param ref: See :meth:`path`.
        :returns: The URL the request is sent to.
        """
        path = self.path(ref)
        return self.api_root if path == "/" else f"{self.api_root}{path}"

    def site_url(self, ref: str) -> str:
        """Absolute URL of the site, as the API writes it in ``@id``.

        :param ref: See :meth:`path`.
        :returns: The URL without ``++api++``.
        """
        path = self.path(ref)
        return self.url if path == "/" else f"{self.url}{path}"

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def token(self) -> str:
        """A JWT for the client's user, for services that only take tokens.

        Volto's own services, such as ``@blocks-schema``, read a Bearer
        token and not basic authentication. A token given to the client is
        returned as is; otherwise the client logs in with ``@login`` once
        and keeps the token.

        :returns: The token, or an empty string for an anonymous client.
        :raises PloneAuthenticationError: If the site refuses the credentials.
        """
        auth = self._http.auth
        if isinstance(auth, TokenAuth):
            return auth.token
        if isinstance(auth, JWTAuth) and auth.token:
            return auth.token
        if not self._token and self.username and self._password:
            answer = self.post(
                "/@login", {"login": self.username, "password": self._password}
            )
            self._token = (answer or {}).get("token", "")
        return self._token

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    @contextmanager
    def recording(self) -> Iterator[list[dict[str, Any]]]:
        """Record the requests sent, or skipped, inside a ``with`` block.

        Used by :mod:`plone_client.operations` to report every request an
        operation made. Recordings can be nested.

        :returns: A list that receives one entry per request: ``method``,
            ``url``, ``status`` and, for skipped requests, ``dry_run``.
        """
        entries: list[dict[str, Any]] = []
        self._recordings.append(entries)
        try:
            yield entries
        finally:
            self._recordings.remove(entries)

    def _record(self, entry: dict[str, Any]) -> None:
        """Add a request to the active recordings.

        :param entry: Description of the request.
        """
        for entries in self._recordings:
            entries.append(dict(entry))

    def _changes_site(self, method: str, path: str) -> bool:
        """Say whether a request could change the site.

        :param method: HTTP method, upper case.
        :param path: Site path of the request.
        :returns: ``False`` for safe methods and read-only ``POST`` services.
        """
        if method in SAFE_METHODS:
            return False
        return not (method == "POST" and path.endswith(READ_ONLY_POSTS))

    def request(
        self,
        method: str,
        ref: str = "/",
        *,
        params: Params = None,
        json: Any = None,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        raise_for_status: bool = True,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Send a request to the site.

        This is the escape hatch for services the managers do not cover,
        such as the ones added by add-ons.

        :param method: HTTP method.
        :param ref: Path or URL of the site, ``@`` services included
            (``/news/@workflow/publish``).
        :param params: Query parameters (see
            :func:`~plone_client.client.encode_params`).
        :param json: Body, serialized as JSON.
        :param content: Raw body, instead of ``json``.
        :param headers: Extra headers for this request.
        :param raise_for_status: Raise
            :class:`~plone_client.exceptions.PloneAPIError` for error answers.
        :param timeout: Seconds to wait, instead of the client's timeout.
        :returns: The response.
        :raises PloneReadOnlyError: If the client is read-only and the request
            could change the site.
        :raises PloneAPIError: If the site answers with an error status.
        :raises PloneConnectionError: If the site cannot be reached.
        """
        method = method.upper()
        path = self.path(ref)
        url = self.api_url(path)
        if self._changes_site(method, path):
            if self.read_only:
                raise PloneReadOnlyError(
                    f"{method} {path} refused: the client is read-only"
                )
            if self.dry_run:
                return self._skip(method, url, params, json, content)
        request = self._http.build_request(
            method,
            url,
            params=encode_params(params),
            json=json,
            content=content,
            headers=headers,
            timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
        )
        response = self._send(request)
        if raise_for_status and response.status_code >= 400:
            raise error_from_response(response)
        return response

    def frontend_request(
        self,
        method: str,
        ref: str = "/",
        *,
        headers: Mapping[str, str] | None = None,
        raise_for_status: bool = True,
    ) -> httpx.Response:
        """Send a read request to the Volto frontend, with a Bearer token.

        For the services that Volto serves itself rather than
        ``plone.restapi``, such as ``@blocks-schema``. The request goes to
        ``frontend_url``, without ``++api++``.

        :param method: ``GET`` or ``HEAD``.
        :param ref: Site path with the service, or a URL of the frontend.
        :param headers: Extra headers for this request.
        :param raise_for_status: Raise
            :class:`~plone_client.exceptions.PloneAPIError` for error answers.
        :returns: The response.
        :raises ValueError: If the method could change the site.
        """
        method = method.upper()
        if method not in SAFE_METHODS:
            raise ValueError(f"{method} is not allowed on the frontend")
        if ref.startswith(f"{self.frontend_url}/") or ref == self.frontend_url:
            ref = ref[len(self.frontend_url) :]
        path = self.path(ref)
        url = self.frontend_url if path == "/" else f"{self.frontend_url}{path}"
        token = self.token()
        request = self._http.build_request(method, url, headers=headers)
        response = self._send(request, auth=TokenAuth(token) if token else httpx.Auth())
        if raise_for_status and response.status_code >= 400:
            raise error_from_response(response)
        return response

    def _send(
        self,
        request: httpx.Request,
        auth: httpx.Auth | None = None,
    ) -> httpx.Response:
        """Send a request, retrying when it is safe to do so.

        Connection failures are retried by the transport. Here, idempotent
        requests are retried when the site answers ``429``, ``502``, ``503``
        or ``504``, honoring ``Retry-After``.

        :param request: The request.
        :param auth: Authentication for this request, instead of the client's.
        :returns: The last response.
        :raises PloneConnectionError: If the site cannot be reached.
        """
        attempts = self.retries + 1 if request.method in IDEMPOTENT_METHODS else 1
        for attempt in range(attempts):
            started = time.monotonic()
            try:
                response = (
                    self._http.send(request)
                    if auth is None
                    else self._http.send(request, auth=auth)
                )
            except httpx.TimeoutException as exc:
                raise PloneTimeoutError(
                    f"{request.method} {request.url}: timed out"
                ) from exc
            except httpx.TransportError as exc:
                raise PloneConnectionError(
                    f"{request.method} {request.url}: {exc}"
                ) from exc
            elapsed = (time.monotonic() - started) * 1000
            logger.debug(
                "%s %s -> %s (%.0f ms)",
                request.method,
                request.url,
                response.status_code,
                elapsed,
            )
            if response.status_code not in RETRY_STATUSES or attempt + 1 == attempts:
                self._record({
                    "method": request.method,
                    "url": str(request.url),
                    "status": response.status_code,
                })
                return response
            wait = _parse_retry_after(response) or self.backoff * 2**attempt
            logger.warning(
                "%s %s answered %s; retrying in %.1fs",
                request.method,
                request.url,
                response.status_code,
                wait,
            )
            response.close()
            time.sleep(wait)
        raise AssertionError("unreachable")  # no cov

    def _skip(
        self,
        method: str,
        url: str,
        params: Params,
        json: Any,
        content: bytes | None,
    ) -> httpx.Response:
        """Record a request instead of sending it.

        :returns: A ``200`` response describing the skipped request.
        """
        entry: dict[str, Any] = {"dry_run": True, "method": method, "url": url}
        if params:
            entry["params"] = encode_params(params)
        if json is not None:
            entry["json"] = json
        if content is not None:
            entry["content_length"] = len(content)
        self.dry_run_log.append(entry)
        self._record({"method": method, "url": url, "status": None, "dry_run": True})
        logger.info("Dry run: %s %s not sent", method, url)
        return httpx.Response(200, json=entry, request=httpx.Request(method, url))

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        """Parsed body of a response.

        :param response: The response.
        :returns: The JSON body, or ``None`` for an empty body.
        """
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, ref: str = "/", **params: Any) -> Any:
        """``GET`` a path and return the JSON body.

        :param ref: Path or URL of the site.
        :param params: Query parameters.
        :returns: The parsed body.
        """
        return self._json(self.request("GET", ref, params=params))

    def post(self, ref: str, data: Any = None, **kwargs: Any) -> Any:
        """``POST`` JSON to a path and return the JSON body.

        :param ref: Path or URL of the site.
        :param data: Body.
        :param kwargs: Extra arguments for :meth:`request`.
        :returns: The parsed body, or ``None``.
        """
        return self._json(self.request("POST", ref, json=data, **kwargs))

    def patch(self, ref: str, data: Any = None, **kwargs: Any) -> Any:
        """``PATCH`` a path with JSON and return the JSON body.

        :param ref: Path or URL of the site.
        :param data: Body.
        :param kwargs: Extra arguments for :meth:`request`.
        :returns: The parsed body, or ``None`` (``plone.restapi`` usually
            answers ``204``).
        """
        return self._json(self.request("PATCH", ref, json=data, **kwargs))

    def put(self, ref: str, data: Any = None, **kwargs: Any) -> Any:
        """``PUT`` JSON to a path and return the JSON body.

        :param ref: Path or URL of the site.
        :param data: Body.
        :param kwargs: Extra arguments for :meth:`request`.
        :returns: The parsed body, or ``None``.
        """
        return self._json(self.request("PUT", ref, json=data, **kwargs))

    def delete(self, ref: str, data: Any = None, **kwargs: Any) -> Any:
        """``DELETE`` a path, with an optional JSON body.

        :param ref: Path or URL of the site.
        :param data: Body; some services (``@aliases``, ``@relations``) read one.
        :param kwargs: Extra arguments for :meth:`request`.
        :returns: The parsed body, or ``None``.
        """
        return self._json(self.request("DELETE", ref, json=data, **kwargs))

    def iter_batches(
        self, ref: str, params: Params = None, *, key: str = "items"
    ) -> Iterator[dict[str, Any]]:
        """Yield every page of a batched answer, following ``batching.next``.

        :param ref: Path or URL of a batched service (``/@search``, a folder,
            ``@users``…).
        :param params: Query parameters of the first page.
        :param key: Key of the list in each page.
        :returns: Each page, as returned by the site.
        """
        pairs: list[tuple[str, Any]] = encode_params(params)
        while True:
            page = self._json(self.request("GET", ref, params=pairs))
            yield page
            next_url = (page.get("batching") or {}).get("next")
            if not next_url or not page.get(key):
                return
            ref = next_url
            pairs = parse_qsl(urlsplit(next_url).query, keep_blank_values=True)

    def iter_items(
        self,
        ref: str,
        params: Params = None,
        *,
        key: str = "items",
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield the items of every page of a batched answer.

        :param ref: Path or URL of a batched service.
        :param params: Query parameters of the first page.
        :param key: Key of the list in each page.
        :param limit: Stop after this many items.
        :returns: Each item.
        """
        count = 0
        for page in self.iter_batches(ref, params, key=key):
            for item in page.get(key) or []:
                if limit is not None and count >= limit:
                    return
                yield item
                count += 1

    def exists(self, ref: str) -> bool:
        """Say whether there is an item at a path.

        :param ref: Path or URL of the site.
        :returns: ``True`` if the item exists, ``False`` on ``404``.
        :raises PloneAPIError: For any other error, such as ``401``.
        """
        response = self.request("GET", ref, raise_for_status=False)
        if response.status_code == 404:
            return False
        if response.status_code >= 400:
            raise error_from_response(response)
        return True

    # ------------------------------------------------------------------
    # Life cycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP connections."""
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"PloneClient({self.url!r})"
