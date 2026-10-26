"""Tests for plone-client.

The unit tests never touch the network: requests go to :class:`FakeSite`,
an :class:`httpx.MockTransport` that records them and answers from routes.
The integration tests, in ``tests/integration``, run against a real Plone
started with Docker.
"""

from collections.abc import Callable
from typing import Any

import httpx
import json


SITE_URL = "http://plone.test/Plone"
API_PREFIX = "/Plone/++api++"

Answer = httpx.Response | Callable[[httpx.Request], httpx.Response]


class FakeSite:
    """A fake Plone site behind an :class:`httpx.MockTransport`.

    Routes are keyed by method and site path (the part after ``++api++``).
    A route holds a list of answers, used in turn; the last one repeats.
    Requests without a route get :attr:`fallback`, which is ``{}`` by default,
    so tests that only check what was sent need no route at all.
    """

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], list[Answer]] = {}
        self.requests: list[httpx.Request] = []
        self.fallback: Answer | None = httpx.Response(200, json={})
        self.transport = httpx.MockTransport(self.handle)

    def add(
        self,
        method: str,
        path: str,
        json: Any = None,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Add an answer to a route.

        :param method: HTTP method.
        :param path: Site path, such as ``/news`` or ``/@search``.
        :param json: Body of the answer; ``None`` for an empty body.
        :param status: Status code.
        :param headers: Response headers.
        """
        response = httpx.Response(status, json=json, headers=headers)
        self.routes.setdefault((method, path), []).append(response)

    def add_callable(
        self, method: str, path: str, func: Callable[[httpx.Request], httpx.Response]
    ) -> None:
        """Answer a route with a function of the request.

        :param method: HTTP method.
        :param path: Site path.
        :param func: Builds the response.
        """
        self.routes.setdefault((method, path), []).append(func)

    @staticmethod
    def site_path(request: httpx.Request) -> str:
        """Site path of a request.

        :param request: The request.
        :returns: The path after ``++api++``.
        """
        path = request.url.path
        if path.startswith(API_PREFIX):
            path = path[len(API_PREFIX) :]
        return path or "/"

    def handle(self, request: httpx.Request) -> httpx.Response:
        """Record a request and answer it.

        :param request: The request.
        :returns: The answer of the route, or the fallback.
        """
        # Snapshot: authentication flows send the same request object again
        # with other headers.
        self.requests.append(
            httpx.Request(
                request.method,
                request.url,
                headers=dict(request.headers),
                content=request.read(),
            )
        )
        answers = self.routes.get((request.method, self.site_path(request)))
        if answers:
            answer = answers.pop(0) if len(answers) > 1 else answers[0]
        elif self.fallback is not None:
            answer = self.fallback
        else:
            answer = httpx.Response(
                404, json={"type": "NotFound", "message": "Resource not found"}
            )
        return answer(request) if callable(answer) else answer

    @property
    def last(self) -> httpx.Request:
        """The last request received."""
        return self.requests[-1]

    def body(self, request: httpx.Request | None = None) -> Any:
        """JSON body of a request.

        :param request: The request; the last one by default.
        :returns: The parsed body, or ``None`` when empty.
        """
        request = request or self.last
        return json.loads(request.content) if request.content else None

    def params(self, request: httpx.Request | None = None) -> list[tuple[str, str]]:
        """Query parameters of a request.

        :param request: The request; the last one by default.
        :returns: Key/value pairs, in order.
        """
        request = request or self.last
        return list(request.url.params.multi_items())


#: A serialized Document, as the API returns it.
DOCUMENT = {
    "@id": f"{SITE_URL}/news/doc",
    "@type": "Document",
    "UID": "0123456789abcdef0123456789abcdef",
    "id": "doc",
    "title": "A document",
    "review_state": "private",
    "items": [],
    "blocks": {},
    "blocks_layout": {"items": []},
}
