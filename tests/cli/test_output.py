from plone_client import exceptions
from plone_client.cli import output

import io
import pytest


@pytest.mark.parametrize(
    "args,expected",
    [
        (["get", "/news"], ["get", "/news"]),
        (["get", "/news", "-f", "title", "-c"], ["-f", "title", "-c", "get", "/news"]),
        (["get", "/news", "--fields=title"], ["--fields=title", "get", "/news"]),
        (
            ["update", "/a", "--title", "x", "-n", "-p", "prod"],
            ["-n", "-p", "prod", "update", "/a", "--title", "x"],
        ),
        (
            ["profile", "add", "x", "--url", "u", "--read-only"],
            ["profile", "add", "x", "--url", "u", "--read-only"],
        ),
        (["request", "GET", "/x", "--", "-c"], ["request", "GET", "/x", "--", "-c"]),
        (["get", "-f"], ["-f", "get"]),
    ],
)
def test_hoist_global_options(args, expected):
    assert output.hoist_global_options(args) == expected


@pytest.mark.parametrize(
    "data,fields,expected",
    [
        ({"a": 1, "b": 2}, [], {"a": 1, "b": 2}),
        ({"a": 1, "b": 2}, ["a", "missing"], {"a": 1}),
        ([{"a": 1, "b": 2}, {"a": 3}], ["a"], [{"a": 1}, {"a": 3}]),
        (
            {"items": [{"a": 1, "b": 2}], "items_total": 1, "batching": {}},
            ["a"],
            {"items_total": 1, "items": [{"a": 1}]},
        ),
        ({"title": "Folder", "items": [{"a": 1}]}, ["title"], {"title": "Folder"}),
        ({"items": [{"a": 1}]}, ["items"], {"items": [{"a": 1}]}),
        ("text", ["a"], "text"),
    ],
)
def test_project(data, fields, expected):
    assert output.project(data, fields) == expected


def test_parse_assignments():
    assert output.parse_assignments([
        "title=Hello = World",
        'subjects:=["a", "b"]',
        "exclude_from_nav:=true",
        "count:=3",
    ]) == {
        "title": "Hello = World",
        "subjects": ["a", "b"],
        "exclude_from_nav": True,
        "count": 3,
    }


@pytest.mark.parametrize(
    "items,message",
    [
        (["title"], "Expected key=value"),
        (["=x"], "Expected key=value"),
        (["a:={"], "Not valid JSON"),
    ],
)
def test_parse_assignments_errors(items, message):
    with pytest.raises(ValueError, match=message):
        output.parse_assignments(items)


def test_read_data(tmp_path, monkeypatch):
    path = tmp_path / "data.json"
    path.write_text('{"title": "From file"}')
    assert output.read_data(None) == {}
    assert output.read_data('{"title": "Inline"}') == {"title": "Inline"}
    assert output.read_data(f"@{path}") == {"title": "From file"}
    monkeypatch.setattr("sys.stdin", io.StringIO('{"title": "Stdin"}'))
    assert output.read_data("-") == {"title": "Stdin"}
    with pytest.raises(ValueError, match="must be a JSON object"):
        output.read_data("[1]")


def test_payload_precedence():
    body = output.payload(
        '{"title": "data", "a": 1}', ["title=set", "b:=2"], title="option", c=None
    )
    assert body == {"title": "option", "a": 1, "b": 2}


@pytest.mark.parametrize(
    "error,code",
    [
        (exceptions.PloneConfigurationError("x"), 3),
        (exceptions.PloneAuthenticationError("x", status_code=401), 4),
        (exceptions.PloneForbiddenError("x", status_code=403), 4),
        (exceptions.PloneNotFoundError("x", status_code=404), 5),
        (exceptions.PloneBadRequestError("x", status_code=400), 6),
        (exceptions.PloneConflictError("x", status_code=409), 6),
        (exceptions.PloneReadOnlyError("x"), 7),
        (exceptions.PloneTimeoutError("x"), 8),
        (exceptions.PloneServerError("x", status_code=500), 9),
        (exceptions.PloneAPIError("x", status_code=418), 1),
        (exceptions.PloneClientError("x"), 1),
    ],
)
def test_exit_code(error, code):
    assert output.exit_code(error) == code
