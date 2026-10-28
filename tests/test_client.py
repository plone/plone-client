from . import SITE_URL
from plone_client import client as client_module
from plone_client import PloneClient
from plone_client.exceptions import PloneAuthenticationError
from plone_client.exceptions import PloneConfigurationError
from plone_client.exceptions import PloneConnectionError
from plone_client.exceptions import PloneNotFoundError
from plone_client.exceptions import PloneReadOnlyError
from plone_client.exceptions import PloneServerError
from plone_client.exceptions import PloneTimeoutError

import base64
import certifi
import httpx
import pytest
import ssl


@pytest.mark.parametrize(
    "ref,expected",
    [
        ("", "/"),
        ("/", "/"),
        ("news", "/news"),
        ("/news/", "/news"),
        ("/news//item", "/news/item"),
        ("/news?b_start=25", "/news"),
        (SITE_URL, "/"),
        (f"{SITE_URL}/", "/"),
        (f"{SITE_URL}/news/item", "/news/item"),
        (f"{SITE_URL}/++api++", "/"),
        (f"{SITE_URL}/++api++/news/@search?b_start=2", "/news/@search"),
        ("/++api++/news", "/news"),
    ],
)
def test_path(client, ref, expected):
    assert client.path(ref) == expected


@pytest.mark.parametrize(
    "ref",
    [
        "https://other.example.org/news",
        f"{SITE_URL}-other/news",
        "http://plone.test/Other",
    ],
)
def test_path_refuses_other_sites(client, ref):
    with pytest.raises(ValueError, match="is not a URL of"):
        client.path(ref)


@pytest.mark.parametrize(
    "api_prefix,ref,api_url,site_url",
    [
        ("++api++", "/", f"{SITE_URL}/++api++", SITE_URL),
        ("++api++", "/news", f"{SITE_URL}/++api++/news", f"{SITE_URL}/news"),
        ("", "/news", f"{SITE_URL}/news", f"{SITE_URL}/news"),
        ("", "/", SITE_URL, SITE_URL),
    ],
)
def test_urls(client_factory, api_prefix, ref, api_url, site_url):
    client = client_factory(api_prefix=api_prefix)
    assert client.api_url(ref) == api_url
    assert client.site_url(ref) == site_url


def test_has_credentials(client_factory):
    assert client_factory().has_credentials is True
    assert client_factory(username="", password="", token="abc").has_credentials
    assert client_factory(username="", password="").has_credentials is False


def test_url_is_required():
    with pytest.raises(ValueError, match="URL of the site is required"):
        PloneClient("")


@pytest.mark.parametrize(
    "params,expected",
    [
        (None, []),
        ({"a": None}, []),
        (
            {"fullobjects": True, "include_items": False},
            [("fullobjects", "true"), ("include_items", "false")],
        ),
        (
            {"portal_type": ["Document", "News Item"]},
            [("portal_type", "Document"), ("portal_type", "News Item")],
        ),
        (
            {"path": {"query": "/news", "depth": 1}},
            [("path.query", "/news"), ("path.depth", "1")],
        ),
        ([("b", 1), ("b", 2)], [("b", "1"), ("b", "2")]),
    ],
)
def test_encode_params(params, expected):
    assert client_module.encode_params(params) == expected


def test_basic_auth_header(client, site):
    client.get("/news")
    expected = "Basic " + base64.b64encode(b"admin:secret").decode()
    assert site.last.headers["Authorization"] == expected
    assert site.last.headers["Accept"] == "application/json"
    assert site.last.headers["User-Agent"].startswith("plone-client/")


def test_token_auth_header(client_factory, site):
    client_factory(username="", password="", token="jwt-token").get("/")
    assert site.last.headers["Authorization"] == "Bearer jwt-token"


def test_anonymous(client_factory, site):
    client_factory(username="", password="").get("/")
    assert "Authorization" not in site.last.headers


def test_extra_headers(client_factory, site):
    client_factory(headers={"X-Test": "1"}).get("/")
    assert site.last.headers["X-Test"] == "1"


def test_json_helpers(client, site):
    site.add("GET", "/news", {"title": "News"})
    site.add("PATCH", "/news", status=204)
    site.add("DELETE", "/news", status=204)
    assert client.get("/news", expand="breadcrumbs") == {"title": "News"}
    assert site.params() == [("expand", "breadcrumbs")]
    assert client.patch("/news", {"title": "New"}) is None
    assert site.body() == {"title": "New"}
    assert client.delete("/news") is None
    assert client.post("/news", {"a": 1}) == {}
    assert client.put("/news", {"a": 1}) == {}
    assert [r.method for r in site.requests] == [
        "GET",
        "PATCH",
        "DELETE",
        "POST",
        "PUT",
    ]


def test_request_raises_for_errors(client, site):
    site.add("GET", "/missing", {"type": "NotFound", "message": "Gone"}, status=404)
    with pytest.raises(PloneNotFoundError, match="Gone"):
        client.get("/missing")
    response = client.request("GET", "/missing", raise_for_status=False)
    assert response.status_code == 404


def test_exists(client, site):
    site.add("GET", "/there", {"title": "There"})
    site.add("GET", "/missing", {}, status=404)
    site.add("GET", "/private", {"type": "Unauthorized", "message": "No"}, status=401)
    assert client.exists("/there") is True
    assert client.exists("/missing") is False
    with pytest.raises(PloneAuthenticationError):
        client.exists("/private")


def test_read_only_refuses_changes(client_factory, site):
    client = client_factory(read_only=True)
    for method in ("POST", "PATCH", "PUT", "DELETE"):
        with pytest.raises(PloneReadOnlyError, match="read-only"):
            client.request(method, "/news")
    assert site.requests == []


def test_read_only_allows_reads_and_read_only_posts(client_factory, site):
    client = client_factory(read_only=True)
    client.get("/news")
    client.post("/@querystring-search", {"query": []})
    client.post("/news/@querystring-search", {"query": []})
    assert [r.method for r in site.requests] == ["GET", "POST", "POST"]


def test_dry_run_records_changes(client_factory, site):
    client = client_factory(dry_run=True)
    result = client.post("/news", {"title": "Hi"}, params={"a": 1})
    client.get("/news")
    assert result == {
        "dry_run": True,
        "method": "POST",
        "url": f"{SITE_URL}/++api++/news",
        "params": [["a", "1"]],
        "json": {"title": "Hi"},
    }
    assert client.dry_run_log == [{**result, "params": [("a", "1")]}]
    assert [r.method for r in site.requests] == ["GET"]


def test_recording(client_factory, site):
    client = client_factory(dry_run=True)
    client.get("/before")
    with client.recording() as outer:
        client.get("/news")
        with client.recording() as inner:
            client.post("/news", {"title": "Hi"})
    client.get("/after")
    assert outer == [
        {"method": "GET", "url": f"{SITE_URL}/++api++/news", "status": 200},
        {
            "method": "POST",
            "url": f"{SITE_URL}/++api++/news",
            "status": None,
            "dry_run": True,
        },
    ]
    assert inner == outer[1:]


def test_token_logs_in_once_with_basic_auth(client, site):
    site.add("POST", "/@login", {"token": "jwt-token"})
    assert client.token() == "jwt-token"
    assert client.token() == "jwt-token"
    assert site.body() == {"login": "admin", "password": "secret"}
    assert len(site.requests) == 1


def test_token_reuses_the_jwt_auth_token(client_factory, site):
    site.add("POST", "/@login", {"token": "jwt-token"})
    client = client_factory(auth_method="jwt")
    client.get("/")
    assert client.token() == "jwt-token"
    assert [r.method for r in site.requests] == ["POST", "GET"]


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"username": "", "password": "", "token": "given"}, "given"),
        ({"username": "", "password": ""}, ""),
    ],
)
def test_token_without_login(client_factory, site, kwargs, expected):
    assert client_factory(**kwargs).token() == expected
    assert site.requests == []


def test_frontend_request(client_factory, site):
    site.add("POST", "/@login", {"token": "jwt-token"})
    client = client_factory(frontend_url="http://www.plone.test/", read_only=True)
    assert client.frontend_url == "http://www.plone.test"
    client.frontend_request("GET", "http://www.plone.test/news/@blocks-schema")
    request = site.last
    assert str(request.url) == "http://www.plone.test/news/@blocks-schema"
    assert request.headers["Authorization"] == "Bearer jwt-token"


def test_frontend_request_defaults_to_the_site_url(client_factory, site):
    client = client_factory(username="", password="")
    assert client.frontend_url == SITE_URL
    site.add("GET", "/Plone/@blocks-schema", status=401)
    with pytest.raises(PloneAuthenticationError):
        client.frontend_request("GET", "/@blocks-schema")
    assert "Authorization" not in site.last.headers
    response = client.frontend_request("GET", "/@blocks-schema", raise_for_status=False)
    assert response.status_code == 401


def test_frontend_request_refuses_changes(client):
    with pytest.raises(ValueError, match="not allowed"):
        client.frontend_request("POST", "/@blocks-schema")


def test_retry_idempotent_requests(client_factory, site, monkeypatch):
    sleeps = []
    monkeypatch.setattr(client_module.time, "sleep", sleeps.append)
    site.add("GET", "/busy", {}, status=503, headers={"Retry-After": "2"})
    site.add("GET", "/busy", {}, status=502)
    site.add("GET", "/busy", {"ok": True})
    client = client_factory(retries=3, backoff=0.5)
    assert client.get("/busy") == {"ok": True}
    assert sleeps == [2.0, 1.0]
    assert len(site.requests) == 3


def test_retries_give_up(client_factory, site, monkeypatch):
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    site.add("GET", "/down", {"message": "Down"}, status=503)
    client = client_factory(retries=2)
    with pytest.raises(PloneServerError):
        client.get("/down")
    assert len(site.requests) == 3


def test_no_retry_for_post(client_factory, site, monkeypatch):
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    site.add("POST", "/news", {"message": "Down"}, status=503)
    client = client_factory(retries=3)
    with pytest.raises(PloneServerError):
        client.post("/news", {})
    assert len(site.requests) == 1


@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx.ConnectError("refused"), PloneConnectionError),
        (httpx.ReadTimeout("slow"), PloneTimeoutError),
    ],
)
def test_transport_errors(client_factory, error, expected):
    def handler(request):
        raise error

    client = client_factory(transport=httpx.MockTransport(handler))
    with pytest.raises(expected):
        client.get("/")


def test_iter_batches_follows_next(client, site):
    def page(request):
        start = request.url.params.get("b_start", "0")
        pages = {
            "0": {
                "items": [{"id": 1}, {"id": 2}],
                "batching": {
                    "next": f"{SITE_URL}/++api++/@search?b_start=2&b_size=2&portal_type=Document"
                },
            },
            "2": {"items": [{"id": 3}], "batching": {}},
        }
        return httpx.Response(200, json=pages[start])

    site.add_callable("GET", "/@search", page)
    items = list(
        client.iter_items("/@search", {"b_size": 2, "portal_type": "Document"})
    )
    assert [item["id"] for item in items] == [1, 2, 3]
    assert site.params(site.requests[1]) == [
        ("b_start", "2"),
        ("b_size", "2"),
        ("portal_type", "Document"),
    ]


def test_iter_items_limit(client, site):
    site.add(
        "GET",
        "/@search",
        {
            "items": [{"id": 1}, {"id": 2}],
            "batching": {"next": f"{SITE_URL}/@search?b_start=2"},
        },
    )
    assert [item["id"] for item in client.iter_items("/@search", limit=1)] == [1]
    assert len(site.requests) == 1


def test_from_env(monkeypatch, site):
    monkeypatch.setenv("REMOTE_URL", SITE_URL)
    monkeypatch.setenv("REMOTE_USER", "editor")
    monkeypatch.setenv("REMOTE_PASSWORD", "pw")
    client = PloneClient.from_env(prefix="REMOTE_", transport=site.transport)
    client.get("/")
    assert (
        site.last.headers["Authorization"]
        == "Basic " + base64.b64encode(b"editor:pw").decode()
    )


def test_from_env_requires_url(monkeypatch):
    monkeypatch.delenv("PLONE_CLIENT_URL", raising=False)
    with pytest.raises(PloneConfigurationError, match="PLONE_CLIENT_URL"):
        PloneClient.from_env()


def test_from_profile(config_file, monkeypatch, site):
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        'current = "dev"\n[profiles.dev]\nurl = "http://plone.test/Plone"\n'
        'username = "admin"\nsecret = "env"\nsecret_env = "DEV_PW"\nread_only = true\n'
    )
    monkeypatch.setenv("DEV_PW", "s3cret")
    client = PloneClient.from_profile(transport=site.transport)
    assert client.read_only is True
    client.get("/")
    assert (
        site.last.headers["Authorization"]
        == "Basic " + base64.b64encode(b"admin:s3cret").decode()
    )


def test_context_manager_and_repr(client_factory):
    with client_factory() as client:
        assert repr(client) == f"PloneClient('{SITE_URL}')"


def test_from_profile_uses_defaults(config_file, site):
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        'current = "dev"\n[defaults]\nretries = 5\nbackoff = 2\n'
        '[profiles.dev]\nurl = "http://plone.test/Plone"\nbackoff = 1\n'
    )
    client = PloneClient.from_profile(transport=site.transport)
    assert (client.retries, client.backoff) == (5, 1)


def test_ssl_verify_passes_booleans_and_contexts_through():
    context = ssl.create_default_context()
    assert client_module.ssl_verify(True) is True
    assert client_module.ssl_verify(False) is False
    assert client_module.ssl_verify(context) is context


def test_ssl_verify_loads_a_ca_bundle_file():
    context = client_module.ssl_verify(certifi.where())
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.cert_store_stats()["x509_ca"] > 0


def test_ssl_verify_accepts_a_directory(tmp_path):
    context = client_module.ssl_verify(str(tmp_path))
    assert isinstance(context, ssl.SSLContext)
    assert context.cert_store_stats()["x509_ca"] == 0


def test_ssl_verify_missing_bundle(tmp_path):
    with pytest.raises(PloneConfigurationError, match="CA bundle not found"):
        PloneClient(SITE_URL, verify=str(tmp_path / "missing.pem"))
