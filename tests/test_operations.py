from . import SITE_URL
from pathlib import PurePath
from plone_client import operations
from plone_client.exceptions import PloneConfigurationError
from plone_client.exceptions import PloneOperationError
from plone_client.exceptions import PloneReadOnlyError

import httpx
import json
import pytest
import sys


PNG = b"\x89PNG\r\n\x1a\n"

VOLTO_NEWS = {"properties": {"title": {}, "blocks": {}, "preview_image_link": {}}}
CLASSIC_NEWS = {"properties": {"title": {}, "image": {}}}

needs_html2blocks = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="collective.html2blocks needs Python 3.12"
)


@pytest.fixture
def fake_create(site):
    """Answer each POST that creates an item with the new item.

    Its ``@id`` is the folder's URL plus the ``id`` or the ``title`` sent,
    and its ``UID`` is ``uid-<id>``.
    """

    def answer(request: httpx.Request) -> httpx.Response:
        path = site.site_path(request)
        if request.method != "POST" or "/@" in path:
            return httpx.Response(200, json={})
        body = json.loads(request.content)
        item_id = body.get("id") or body["title"].lower()
        return httpx.Response(
            201,
            json={
                "@id": f"{SITE_URL}{path.rstrip('/')}/{item_id}",
                "@type": body["@type"],
                "UID": f"uid-{item_id}",
                "id": item_id,
                "title": body.get("title"),
                "review_state": "private",
            },
        )

    site.fallback = answer
    return site


@pytest.fixture
def files(tmp_path):
    """A photo, a second photo and a PDF."""
    paths = []
    for name, data in (("lead.png", PNG), ("photo.png", PNG), ("doc.pdf", b"%PDF")):
        path = tmp_path / name
        path.write_bytes(data)
        paths.append(path)
    return paths


def _calls(site):
    return [(r.method, site.site_path(r)) for r in site.requests]


class TestCreateWithFiles:
    def test_volto_lead_image(self, client, fake_create, files):
        site = fake_create
        site.add("GET", "/@types/News Item", VOLTO_NEWS)
        site.add(
            "GET", "/news/office", {**VOLTO_NEWS, "@id": f"{SITE_URL}/news/office"}
        )
        result = operations.create_with_files(
            client,
            "/news",
            "News Item",
            files,
            title="Office",
            id="office",
            publish="publish",
        )
        assert _calls(site) == [
            ("GET", "/@types/News Item"),
            ("POST", "/news"),
            ("POST", "/news/office"),
            ("POST", "/news/office"),
            ("POST", "/news/office"),
            ("PATCH", "/news/office"),
            ("POST", "/news/office/@workflow/publish"),
            ("GET", "/news/office"),
        ]
        created = json.loads(site.requests[1].content)
        assert created["title"] == "Office"
        assert [b["@type"] for b in created["blocks"].values()] == [
            "title",
            "description",
        ]
        uploads = [json.loads(r.content) for r in site.requests[2:5]]
        assert [u["@type"] for u in uploads] == ["Image", "Image", "File"]
        assert json.loads(site.requests[5].content) == {
            "preview_image_link": "uid-lead.png"
        }
        assert [entry["id"] for entry in result.created] == [
            "office",
            "lead.png",
            "photo.png",
            "doc.pdf",
        ]
        assert result.created[1]["source"] == str(files[0])
        assert result.changed == [
            {
                "@id": f"{SITE_URL}/news/office",
                "fields": {"preview_image_link": f"{SITE_URL}/news/office/lead.png"},
            },
            {"@id": f"{SITE_URL}/news/office", "transition": "publish"},
        ]
        assert len(result.requests) == 8
        assert result.requests[0]["status"] == 200
        assert result.item["@id"] == f"{SITE_URL}/news/office"

    def test_image_field(self, client, fake_create, files):
        site = fake_create
        site.add("GET", "/@types/News Item", CLASSIC_NEWS)
        result = operations.create_with_files(
            client,
            "/news",
            "News Item",
            files[1:],
            data={"title": "Office"},
            lead_image=0,
        )
        created = json.loads(site.requests[1].content)
        assert created["image"]["filename"] == "photo.png"
        assert "blocks" not in created
        assert [entry["id"] for entry in result.created] == ["office", "doc.pdf"]
        assert result.changed == []

    def test_first_image_is_skipped_without_a_lead_field(
        self, client, fake_create, files
    ):
        fake_create.add("GET", "/@types/Event", {"properties": {"title": {}}})
        result = operations.create_with_files(
            client, "/events", "Event", files, title="Party"
        )
        assert len(result.created) == 4
        assert "PATCH" not in [method for method, _ in _calls(fake_create)]

    def test_explicit_lead_needs_a_lead_field(self, client, fake_create, files):
        fake_create.add("GET", "/@types/Event", {"properties": {"title": {}}})
        with pytest.raises(ValueError, match="has no lead image field"):
            operations.create_with_files(
                client, "/events", "Event", files, title="Party", lead_image=1
            )
        assert _calls(fake_create) == [("GET", "/@types/Event")]

    @pytest.mark.parametrize(
        "lead_image,message", [(2, "is not an image"), (5, "is not one of the files")]
    )
    def test_invalid_lead_sends_nothing(self, client, site, files, lead_image, message):
        with pytest.raises(ValueError, match=message):
            operations.create_with_files(
                client, "/news", "News Item", files, lead_image=lead_image
            )
        assert site.requests == []

    def test_missing_file_sends_nothing(self, client, site, tmp_path):
        with pytest.raises(ValueError, match="Not a file"):
            operations.create_with_files(
                client, "/news", "News Item", [tmp_path / "nope.png"]
            )
        assert site.requests == []

    def test_dry_run(self, client_factory, site, files):
        site.add("GET", "/@types/News Item", VOLTO_NEWS)
        client = client_factory(dry_run=True)
        result = operations.create_with_files(
            client,
            "/news",
            "News Item",
            files[:1],
            title="Our Office",
            publish="publish",
        )
        assert [r.method for r in site.requests] == ["GET"]
        assert result.dry_run is True
        planned = f"{SITE_URL}/news/our-office"
        assert result.item == {
            "@id": planned,
            "@type": "News Item",
            "id": "our-office",
            "title": "Our Office",
            "planned": True,
        }
        assert result.created[1]["@id"] == f"{planned}/lead.png"
        patch = client.dry_run_log[2]
        assert patch["url"] == f"{SITE_URL}/++api++/news/our-office"
        assert patch["json"] == {"preview_image_link": f"{planned}/lead.png"}
        assert [entry.get("dry_run", False) for entry in result.requests] == [
            False,
            True,
            True,
            True,
            True,
        ]

    def test_failure_part_way(self, client, fake_create, files):
        site = fake_create
        site.add("GET", "/@types/News Item", VOLTO_NEWS)
        answers = iter([None, httpx.Response(400, json={"message": "Bad file"})])

        def upload(request):
            answer = next(answers)
            return answer or site.fallback(request)

        site.add_callable("POST", "/news/office", upload)
        with pytest.raises(
            PloneOperationError, match="create_with_files stopped"
        ) as info:
            operations.create_with_files(
                client, "/news", "News Item", files, title="Office"
            )
        result = info.value.result
        assert [entry["id"] for entry in result.created] == ["office", "lead.png"]
        assert result.error["status_code"] == 400
        assert result.error["message"] == "Bad file"
        assert result.requests[-1]["status"] == 400
        assert info.value.__cause__.status_code == 400

    def test_read_only(self, client_factory, site, files):
        site.add("GET", "/@types/News Item", VOLTO_NEWS)
        client = client_factory(read_only=True)
        with pytest.raises(PloneOperationError) as info:
            operations.create_with_files(client, "/news", "News Item", files)
        assert isinstance(info.value.__cause__, PloneReadOnlyError)
        assert info.value.result.created == []


class TestCreatePage:
    @needs_html2blocks
    def test_markdown(self, client, fake_create):
        fake_create.add(
            "GET",
            "/docs/getting started",
            {"@id": f"{SITE_URL}/docs/getting-started", "review_state": "published"},
        )
        result = operations.create_page(
            client,
            "/docs",
            "# Getting started\n\nSome *text*.\n\n- a\n- b\n",
            data={"subjects": ["intro"]},
            publish="publish",
        )
        site = fake_create
        body = json.loads(site.requests[0].content)
        assert body["title"] == "Getting started"
        assert body["subjects"] == ["intro"]
        types = [body["blocks"][i]["@type"] for i in body["blocks_layout"]["items"]]
        assert types == ["title", "description", "slate", "slate"]
        texts = [block.get("plaintext") for block in body["blocks"].values()]
        assert "Getting started" not in texts
        assert _calls(site)[1:] == [
            ("POST", "/docs/getting started/@workflow/publish"),
            ("GET", "/docs/getting started"),
        ]
        assert result.item == {
            "@id": f"{SITE_URL}/docs/getting-started",
            "review_state": "published",
        }

    @needs_html2blocks
    def test_html_with_title(self, client, fake_create):
        operations.create_page(
            client,
            "/docs",
            "<h1>Heading</h1><p>Text</p>",
            source_format="html",
            title="Given",
            description="Short",
        )
        body = fake_create.body(fake_create.requests[0])
        assert body["title"] == "Given"
        assert body["description"] == "Short"
        texts = [block.get("plaintext") for block in body["blocks"].values()]
        assert "Heading" in texts

    def test_title_is_required(self, client, site):
        with pytest.raises(ValueError, match="A title is needed"):
            operations.create_page(client, "/docs", "Just text")
        assert site.requests == []

    def test_without_html2blocks(self, client, monkeypatch):
        monkeypatch.setitem(sys.modules, "collective.html2blocks", None)
        with pytest.raises(PloneConfigurationError, match="'markdown' extra"):
            operations.create_page(client, "/docs", "# Title\n\nText")

    @needs_html2blocks
    def test_portal_type(self, client, fake_create):
        operations.create_page(client, "/docs", "# Hello\n\nText.", portal_type="Post")
        assert fake_create.body()["@type"] == "Post"

    @needs_html2blocks
    def test_blocks_setting_of_the_site_and_the_call(self, client_factory, site):
        client = client_factory(
            blocks={"codeBlock": {"style": "dark"}, "slateTable": False}
        )
        site.fallback = httpx.Response(201, json={"@id": f"{SITE_URL}/docs/code"})
        source = "# Code\n\n```python\nprint(1)\n```\n\n| a |\n|---|\n| 1 |\n"
        operations.create_page(
            client, "/docs", source, blocks_setting={"codeBlock": {"style": "light"}}
        )
        found = list(site.body()["blocks"].values())
        types = [block["@type"] for block in found]
        assert types == ["title", "description", "codeBlock", "slate"]
        # the call's options replace the site's, and the site's table setting stays
        assert found[2]["style"] == "light"

    @needs_html2blocks
    def test_invalid_blocks_setting_sends_nothing(self, client, site):
        with pytest.raises(ValueError, match="Unknown block type nope"):
            operations.create_page(
                client, "/docs", "# Hi\n\nText", blocks_setting={"nope": True}
            )
        assert site.requests == []

    @needs_html2blocks
    def test_files_and_lead_image(self, client, fake_create, files):
        site = fake_create
        site.add("GET", "/@types/Document", VOLTO_NEWS)
        result = operations.create_page(
            client, "/docs", "# Office\n\nText.", files=files
        )
        assert _calls(site) == [
            ("GET", "/@types/Document"),
            ("POST", "/docs"),
            ("POST", "/docs/office"),
            ("POST", "/docs/office"),
            ("POST", "/docs/office"),
            ("PATCH", "/docs/office"),
        ]
        assert [entry["id"] for entry in result.created] == [
            "office",
            "lead.png",
            "photo.png",
            "doc.pdf",
        ]
        assert result.changed == [
            {
                "@id": f"{SITE_URL}/docs/office",
                "fields": {"preview_image_link": f"{SITE_URL}/docs/office/lead.png"},
            }
        ]
        assert json.loads(site.requests[-1].content) == {
            "preview_image_link": "uid-lead.png"
        }

    @needs_html2blocks
    def test_lead_image_in_the_image_field(self, client, fake_create, files):
        site = fake_create
        site.add("GET", "/@types/Document", CLASSIC_NEWS)
        result = operations.create_page(
            client, "/docs", "# Office\n\nText.", files=files[1:], lead_image=0
        )
        assert site.body(site.requests[1])["image"]["filename"] == "photo.png"
        assert [entry["id"] for entry in result.created] == ["office", "doc.pdf"]
        assert result.changed == []

    @needs_html2blocks
    def test_no_lead_image(self, client, fake_create, files):
        result = operations.create_page(
            client, "/docs", "# Office\n\nText.", files=files, lead_image=None
        )
        assert _calls(fake_create) == [
            ("POST", "/docs"),
            ("POST", "/docs/office"),
            ("POST", "/docs/office"),
            ("POST", "/docs/office"),
        ]
        assert len(result.created) == 4
        assert result.changed == []

    @needs_html2blocks
    def test_explicit_lead_needs_a_lead_field(self, client, fake_create, files):
        fake_create.add(
            "GET", "/@types/Document", {"properties": {"title": {}, "blocks": {}}}
        )
        with pytest.raises(ValueError, match="has no lead image field"):
            operations.create_page(
                client, "/docs", "# Office\n\nText.", files=files, lead_image=0
            )
        assert _calls(fake_create) == [("GET", "/@types/Document")]

    @needs_html2blocks
    def test_invalid_lead_sends_nothing(self, client, site, files):
        with pytest.raises(ValueError, match="is not an image"):
            operations.create_page(
                client, "/docs", "# Office\n\nText.", files=files, lead_image=2
            )
        assert site.requests == []


@pytest.mark.parametrize(
    "source,source_format,expected",
    [
        ("# Hello #\n\nText", "markdown", ("Hello", "Text")),
        ("\n#  Hello\nText", "markdown", ("Hello", "Text")),
        ("## Not h1\n", "markdown", ("", "## Not h1\n")),
        (
            "<h1 class='x'>Hi <em>there</em></h1>\n<p>T</p>",
            "html",
            ("Hi there", "<p>T</p>"),
        ),
        ("<p>T</p>", "html", ("", "<p>T</p>")),
    ],
)
def test_split_title(source, source_format, expected):
    assert operations.split_title(source, source_format) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Our Office", "our-office"),
        ("Ação 2026!", "acao-2026"),
        ("report.pdf", "report.pdf"),
        ("???", "item"),
    ],
)
def test_slug(text, expected):
    assert operations.slug(text) == expected


@pytest.fixture
def tree(tmp_path):
    """A local folder to upload."""
    root = tmp_path / "site"
    (root / "Guides").mkdir(parents=True)
    (root / "Guides" / "index.md").write_text("# The guides\n\nRead them.\n")
    (root / "Guides" / "photo.png").write_bytes(PNG)
    (root / "about.md").write_text("# About us\n\nWho we are.\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("")
    (root / ".DS_Store").write_bytes(b"")
    return root


class TestUploadTree:
    def test_upload(self, client, fake_create, tree):
        site = fake_create
        result = operations.upload_tree(client, tree, "/docs", publish="publish")
        assert _calls(site) == [
            ("GET", "/docs"),
            ("POST", "/docs"),
            ("POST", "/docs"),
            ("POST", "/docs/guides/@workflow/publish"),
            ("POST", "/docs/guides"),
            ("POST", "/docs/guides"),
        ]
        about, guides = (site.body(r) for r in site.requests[1:3])
        assert about["@type"] == "File"
        assert guides["@type"] == "Document"
        assert guides["title"] == "Guides"
        assert guides["id"] == "guides"
        sources = [entry["source"] for entry in result.created]
        assert sources == [
            str(tree / "about.md"),
            str(tree / "Guides"),
            str(tree / "Guides" / "index.md"),
            str(tree / "Guides" / "photo.png"),
        ]

    @needs_html2blocks
    def test_convert_pages(self, client, fake_create, tree):
        site = fake_create
        operations.upload_tree(client, tree, "/docs", convert_pages=True)
        about, guides, photo = (site.body(r) for r in site.requests[1:])
        assert (about["@type"], about["id"], about["title"]) == (
            "Document",
            "about",
            "About us",
        )
        assert (guides["id"], guides["title"]) == ("guides", "The guides")
        for page, text in ((about, "Who we are."), (guides, "Read them.")):
            texts = [block.get("plaintext") for block in page["blocks"].values()]
            # the heading is the title, not a text block
            assert texts == [None, None, text]
        assert photo["@type"] == "Image"

    @needs_html2blocks
    def test_convert_pages_with_a_blocks_setting(self, client, fake_create, tmp_path):
        (tmp_path / "code.md").write_text("# Code\n\n```sh\nls\n```\n")
        operations.upload_tree(
            client,
            tmp_path,
            "/docs",
            convert_pages=True,
            blocks_setting={"codeBlock": True},
        )
        types = [block["@type"] for block in fake_create.body()["blocks"].values()]
        assert types == ["title", "description", "codeBlock"]

    @needs_html2blocks
    def test_invalid_blocks_setting_sends_nothing(self, client, site, tree):
        with pytest.raises(ValueError, match="cannot be disabled"):
            operations.upload_tree(
                client,
                tree,
                "/docs",
                convert_pages=True,
                blocks_setting={"slate": False},
            )
        assert site.requests == []

    def test_blocks_setting_is_ignored_without_pages(self, client, fake_create, tree):
        operations.upload_tree(client, tree, "/docs", blocks_setting={"nope": True})
        assert fake_create.requests

    @needs_html2blocks
    def test_convert_pages_without_heading(self, client, fake_create, tmp_path):
        (tmp_path / "notes.md").write_text("Just text.\n")
        operations.upload_tree(client, tmp_path, "/docs", convert_pages=True)
        assert fake_create.body()["title"] == "notes"

    def test_hidden(self, client, fake_create, tree):
        result = operations.upload_tree(client, tree, "/docs", include_hidden=True)
        names = [PurePath(entry["source"]).name for entry in result.created]
        assert ".git" in names
        assert ".DS_Store" in names

    def test_dry_run(self, client_factory, site, tree):
        client = client_factory(dry_run=True)
        result = operations.upload_tree(client, tree, "/docs")
        assert [r.method for r in site.requests] == ["GET"]
        assert [entry["@id"] for entry in result.created] == [
            f"{SITE_URL}/docs/about.md",
            f"{SITE_URL}/docs/guides",
            f"{SITE_URL}/docs/guides/index.md",
            f"{SITE_URL}/docs/guides/photo.png",
        ]
        assert all(entry["planned"] for entry in result.created)

    def test_missing_parent(self, client, site, tree):
        site.add("GET", "/nope", {"message": "Not found"}, status=404)
        with pytest.raises(PloneOperationError) as info:
            operations.upload_tree(client, tree, "/nope")
        assert info.value.result.created == []

    def test_source_must_be_a_folder(self, client, site, tmp_path):
        with pytest.raises(ValueError, match="Not a folder"):
            operations.upload_tree(client, tmp_path / "nope", "/docs")
        assert site.requests == []


class TestTransfer:
    def _routes(self, site, service):
        site.add("GET", "/archive", {"is_folderish": True})
        site.add("GET", "/news/@search", {"items_total": 3})
        site.add("GET", "/archive/news/@search", {"items_total": 3})
        site.add(
            "POST",
            f"/archive/@{service}",
            [{"source": f"{SITE_URL}/news", "target": f"{SITE_URL}/archive/news"}],
        )

    def test_copy(self, client, site):
        self._routes(site, "copy")
        result = operations.copy_items(client, "/news", "/archive")
        assert result.created == [
            {
                "source": f"{SITE_URL}/news",
                "@id": f"{SITE_URL}/archive/news",
                "items": 3,
                "items_after": 3,
            }
        ]
        assert site.body(site.requests[2]) == {"source": ["/news"]}

    def test_move(self, client, site):
        self._routes(site, "move")
        result = operations.move_items(client, ["/news"], "/archive")
        assert result.created == []
        assert result.changed[0]["@id"] == f"{SITE_URL}/archive/news"

    def test_dry_run(self, client_factory, site):
        self._routes(site, "move")
        client = client_factory(dry_run=True)
        result = operations.move_items(client, "/news", "/archive")
        assert result.changed == [
            {
                "source": f"{SITE_URL}/news",
                "@id": f"{SITE_URL}/archive/news",
                "items": 3,
                "planned": True,
            }
        ]

    def test_target_must_be_a_folder(self, client, site):
        site.add("GET", "/page", {"is_folderish": False})
        with pytest.raises(ValueError, match="is not a folder"):
            operations.copy_items(client, "/news", "/page")


def test_result_to_dict():
    result = operations.OperationResult(operation="x", dry_run=False)
    assert result.to_dict() == {
        "operation": "x",
        "dry_run": False,
        "created": [],
        "changed": [],
        "requests": [],
    }


def block_page():
    return {
        "@id": f"{SITE_URL}/page",
        "@type": "Document",
        "id": "page",
        "title": "Page",
        "blocks": {
            "t": {"@type": "title"},
            "d": {"@type": "description"},
            "a": {"@type": "slate", "plaintext": "First"},
            "g": {
                "@type": "gridBlock",
                "blocks": {"g1": {"@type": "teaser", "href": [{"@id": "/x"}]}},
                "blocks_layout": {"items": ["g1"]},
            },
        },
        "blocks_layout": {"items": ["t", "d", "a", "g"]},
    }


@pytest.fixture
def page(site):
    site.add("GET", "/page", block_page())
    return site


def _saved(site):
    """The blocks the last PATCH sent."""
    request = site.requests[-1]
    assert (request.method, site.site_path(request)) == ("PATCH", "/page")
    return json.loads(request.content)


def _order(body):
    return body["blocks_layout"]["items"]


class TestAddBlocks:
    def test_at_the_end(self, client, page):
        result = operations.add_blocks(
            client, "/page", [{"@type": "teaser", "href": "/news"}]
        )
        body = _saved(page)
        (new,) = result.changed[0]["added"]
        assert _order(body) == ["t", "d", "a", "g", new]
        assert body["blocks"][new] == {"@type": "teaser", "href": [{"@id": "/news"}]}
        assert result.item["@id"] == f"{SITE_URL}/page"
        assert [entry["id"] for entry in result.item["blocks"]] == _order(body)

    def test_after_a_block(self, client, page):
        result = operations.add_blocks(
            client, "/page", [{"@type": "slate"}, {"@type": "image"}], after="d"
        )
        new = result.changed[0]["added"]
        assert _order(_saved(page)) == ["t", "d", *new, "a", "g"]

    def test_after_a_block_in_a_container(self, client, page):
        result = operations.add_blocks(
            client, "/page", [{"@type": "teaser", "href": "/y"}], after="g1"
        )
        body = _saved(page)
        (new,) = result.changed[0]["added"]
        assert _order(body) == ["t", "d", "a", "g"]
        assert body["blocks"]["g"]["blocks_layout"]["items"] == ["g1", new]
        assert new in body["blocks"]["g"]["blocks"]

    def test_at_a_position(self, client, page):
        result = operations.add_blocks(
            client, "/page", [{"@type": "slate"}], position=0
        )
        (new,) = result.changed[0]["added"]
        # The title block stays first
        assert _order(_saved(page)) == ["t", new, "d", "a", "g"]

    @pytest.mark.parametrize(
        "kwargs,message",
        [
            ({"after": "a", "position": 1}, "either after or position"),
            ({"after": "nope"}, "No block 'nope'"),
            ({"position": 5}, "between 0 and 4"),
        ],
    )
    def test_refused_changes_send_nothing(self, client, page, kwargs, message):
        with pytest.raises(ValueError, match=message):
            operations.add_blocks(client, "/page", [{"@type": "slate"}], **kwargs)
        assert [r.method for r in page.requests] in ([], ["GET"])

    def test_blocks_need_a_type(self, client, page):
        with pytest.raises(ValueError, match="needs an @type"):
            operations.add_blocks(client, "/page", [{"href": "/a"}])
        with pytest.raises(ValueError, match="No blocks"):
            operations.add_blocks(client, "/page", [])
        assert page.requests == []

    def test_item_without_blocks(self, client, site):
        site.add("GET", "/file", {"@id": f"{SITE_URL}/file"})
        with pytest.raises(ValueError, match="/file has no blocks"):
            operations.add_blocks(client, "/file", [{"@type": "slate"}])
        assert _calls(site) == [("GET", "/file")]

    def test_dry_run(self, client_factory, page):
        client = client_factory(dry_run=True)
        result = operations.add_blocks(client, "/page", [{"@type": "slate"}])
        assert result.dry_run
        assert _calls(page) == [("GET", "/page")]
        assert len(result.item["blocks"]) == 5

    def test_layout_is_tidied(self, client, site):
        item = block_page()
        item["blocks_layout"] = {"items": ["a", "gone", "t"]}
        site.add("GET", "/page", item)
        result = operations.add_blocks(client, "/page", [{"@type": "slate"}])
        (new,) = result.changed[0]["added"]
        assert _order(_saved(site)) == ["t", "a", new, "d", "g"]


class TestUpdateBlock:
    def test_merge(self, client, page):
        result = operations.update_block(client, "/page", "a", {"plaintext": "New"})
        assert _saved(page)["blocks"]["a"] == {"@type": "slate", "plaintext": "New"}
        assert result.changed[0]["updated"] == ["a"]

    def test_replace_keeps_the_type(self, client, page):
        operations.update_block(
            client, "/page", "g1", {"href": "/z", "overwrite": True}, replace=True
        )
        assert _saved(page)["blocks"]["g"]["blocks"]["g1"] == {
            "@type": "teaser",
            "href": [{"@id": "/z"}],
            "overwrite": True,
        }

    def test_missing_block(self, client, page):
        with pytest.raises(ValueError, match="No block 'nope'"):
            operations.update_block(client, "/page", "nope", {"x": 1})
        assert _calls(page) == [("GET", "/page")]


class TestRemoveBlocks:
    def test_remove(self, client, page):
        result = operations.remove_blocks(client, "/page", ["a", "g1"])
        body = _saved(page)
        assert _order(body) == ["t", "d", "g"]
        assert "a" not in body["blocks"]
        assert body["blocks"]["g"]["blocks"] == {}
        assert body["blocks"]["g"]["blocks_layout"]["items"] == []
        assert result.changed[0]["removed"] == ["a", "g1"]

    def test_block_missing_from_the_layout(self, client, site):
        item = block_page()
        item["blocks_layout"] = {"items": ["t"]}
        site.add("GET", "/page", item)
        operations.remove_blocks(client, "/page", "a")
        assert _order(_saved(site)) == ["t", "d", "g"]

    def test_missing_block_sends_nothing(self, client, page):
        with pytest.raises(ValueError, match="No block 'nope'"):
            operations.remove_blocks(client, "/page", ["a", "nope"])
        assert _calls(page) == [("GET", "/page")]


class TestSetBlocks:
    def test_keeps_title_and_description(self, client, page):
        result = operations.set_blocks(
            client, "/page", [{"@type": "slate", "plaintext": "Only"}]
        )
        body = _saved(page)
        (new,) = result.changed[0]["added"]
        assert _order(body) == ["t", "d", new]
        assert set(body["blocks"]) == {"t", "d", new}
        assert result.changed[0]["removed"] == ["a", "g"]

    def test_given_title_replaces_the_old_one(self, client, page):
        result = operations.set_blocks(
            client, "/page", [{"@type": "slate"}, {"@type": "title"}]
        )
        body = _saved(page)
        slate, title = result.changed[0]["added"]
        assert _order(body) == [title, "d", slate]
        assert result.changed[0]["removed"] == ["t", "a", "g"]
