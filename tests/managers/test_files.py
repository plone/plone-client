from .. import SITE_URL
from plone_client import file_data
from plone_client.exceptions import PloneClientError

import base64
import httpx
import pytest


def test_file_data_from_path(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF-1.4")
    assert file_data(path) == {
        "data": base64.b64encode(b"%PDF-1.4").decode(),
        "encoding": "base64",
        "filename": "report.pdf",
        "content-type": "application/pdf",
    }


def test_file_data_from_bytes():
    value = file_data(b"abc", filename="data.bin", content_type="application/x-test")
    assert value["content-type"] == "application/x-test"
    assert value["filename"] == "data.bin"


def test_file_data_needs_a_filename_for_bytes():
    with pytest.raises(ValueError, match="filename is required"):
        file_data(b"abc")


@pytest.mark.parametrize(
    "filename,portal_type,field",
    [("photo.png", "Image", "image"), ("notes.txt", "File", "file")],
)
def test_upload_picks_type_and_field(client, site, filename, portal_type, field):
    client.files.upload("/media", b"data", filename=filename, id="x")
    body = site.body()
    assert (site.last.method, site.site_path(site.last)) == ("POST", "/media")
    assert body["@type"] == portal_type
    assert body["title"] == filename
    assert body["id"] == "x"
    assert body[field]["data"] == base64.b64encode(b"data").decode()


def test_upload_with_explicit_type(client, site):
    client.files.upload("/media", b"data", filename="a.png", portal_type="File")
    assert site.body()["@type"] == "File"
    assert "file" in site.body()


def test_replace(client, site):
    client.files.replace("/media/a.png", b"new", filename="b.png", field="image")
    assert site.last.method == "PATCH"
    assert site.body()["image"]["filename"] == "b.png"
    assert "Prefer" not in site.last.headers


@pytest.mark.parametrize(
    "call,path",
    [
        (lambda c: c.files.download("/media/a.txt"), "/media/a.txt/@@download/file"),
        (
            lambda c: c.files.download("/media/a.png", field="image"),
            "/media/a.png/@@download/image",
        ),
        (
            lambda c: c.files.image_scale("/media/a.png", scale="thumb"),
            "/media/a.png/@@images/image/thumb",
        ),
    ],
)
def test_downloads(client, site, call, path):
    site.add_callable(
        "GET", path, lambda request: httpx.Response(200, content=b"bytes")
    )
    assert call(client) == b"bytes"


def _tus_routes(site, service, final_location):
    upload_url = f"{SITE_URL}/++api++{service}/abc"
    site.add("POST", service, status=201, headers={"Location": upload_url})

    def patch(request):
        offset = int(request.headers["Upload-Offset"]) + len(request.content)
        headers = {"Upload-Offset": str(offset)}
        if offset >= 10 and final_location:
            headers["Location"] = final_location
        return httpx.Response(204, headers=headers)

    site.add_callable("PATCH", f"{service}/abc", patch)


def test_tus_upload(client, site):
    _tus_routes(site, "/media/@tus-upload", f"{SITE_URL}/media/big.txt")
    location = client.files.tus_upload(
        "/media", b"0123456789", filename="big.txt", chunk_size=4
    )
    assert location == f"{SITE_URL}/media/big.txt"
    post, *patches = site.requests
    assert post.headers["Upload-Length"] == "10"
    metadata = dict(
        pair.split(" ") for pair in post.headers["Upload-Metadata"].split(",")
    )
    decoded = {key: base64.b64decode(value).decode() for key, value in metadata.items()}
    assert decoded == {
        "filename": "big.txt",
        "content-type": "text/plain",
        "@type": "File",
        "fieldname": "file",
    }
    assert [p.headers["Upload-Offset"] for p in patches] == ["0", "4", "8"]
    assert [p.content for p in patches] == [b"0123", b"4567", b"89"]
    assert patches[0].headers["Content-Type"] == "application/offset+octet-stream"


def test_tus_upload_without_location_fails(client, site):
    _tus_routes(site, "/media/@tus-upload", "")
    with pytest.raises(PloneClientError, match="did not store the file"):
        client.files.tus_upload("/media", b"0123456789", filename="big.txt")


def test_tus_replace(client, site):
    _tus_routes(site, "/media/big.txt/@tus-replace", f"{SITE_URL}/media/big.txt")
    location = client.files.tus_replace(
        "/media/big.txt", b"0123456789", filename="big.txt"
    )
    assert location == f"{SITE_URL}/media/big.txt"
    assert site.site_path(site.requests[0]) == "/media/big.txt/@tus-replace"
