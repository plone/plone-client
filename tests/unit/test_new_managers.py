"""Unit tests for new resource managers (files, relations, working copy, blocks, db)."""

from __future__ import annotations

from plone_client import PloneClient
from plone_client.config import PloneClientConfig

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


@pytest.fixture()
def cli() -> PloneClient:
    cfg = PloneClientConfig(
        base_url=BASE,
        token="test-token",
        max_retries=0,
        retry_backoff=0,
    )
    return PloneClient(config=cfg)


# ---------------------------------------------------------------------------
# FilesManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilesManager:
    @resp_mock.activate
    def test_upload_creates_file_object(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/documents",
            json={"@id": f"{BASE}/documents/report-pdf", "@type": "File"},
            status=201,
        )
        result = cli.files.upload(
            "/documents",
            "report.pdf",
            b"%PDF-1.4 fake",
            content_type="application/pdf",
        )
        assert result["@type"] == "File"

    @resp_mock.activate
    def test_upload_detects_image_type(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/images",
            json={"@type": "Image"},
            status=201,
        )
        result = cli.files.upload(
            "/images",
            "photo.jpg",
            b"\xff\xd8\xff fake-jpeg",
            content_type="image/jpeg",
        )
        assert result["@type"] == "Image"

    @resp_mock.activate
    def test_update_file_field(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.PATCH,
            f"{BASE}/documents/report",
            json={"@id": f"{BASE}/documents/report"},
        )
        result = cli.files.update_file_field(
            "/documents/report",
            b"new content",
            field="file",
            filename="report.pdf",
        )
        assert "@id" in result

    @resp_mock.activate
    def test_download(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/documents/report/@download/file",
            body=b"file-bytes",
        )
        data = cli.files.download("/documents/report")
        assert data == b"file-bytes"

    @resp_mock.activate
    def test_image_scales(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/news/article/@images",
            json={"original": {"width": 1920, "height": 1080}},
        )
        result = cli.files.image_scales("/news/article")
        assert "original" in result

    @resp_mock.activate
    def test_image_scale(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/news/article/@images/image/preview",
            json={"width": 400, "height": 300, "download": f"{BASE}/@@images/preview"},
        )
        result = cli.files.image_scale("/news/article", "image", "preview")
        assert result["width"] == 400


# ---------------------------------------------------------------------------
# RelationsManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelationsManager:
    @resp_mock.activate
    def test_list_relations(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@relations",
            json={"items": [], "items_total": 0},
        )
        result = cli.relations.list()
        assert result["items_total"] == 0

    @resp_mock.activate
    def test_create_relation(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@relations",
            json={"source": "/doc-a", "target": "/doc-b", "relation": "relatedItems"},
            status=201,
        )
        result = cli.relations.create("/doc-a", "/doc-b")
        assert result["relation"] == "relatedItems"

    @resp_mock.activate
    def test_broken_relations(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@brokenrelations",
            json={"items": [], "items_total": 0},
        )
        result = cli.relations.broken()
        assert "items" in result

    @resp_mock.activate
    def test_rebuild(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@relations",
            json={"message": "Relations rebuilt"},
        )
        result = cli.relations.rebuild()
        assert "message" in result


# ---------------------------------------------------------------------------
# WorkingCopyManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWorkingCopyManager:
    @resp_mock.activate
    def test_checkout(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-doc/@workingcopy",
            json={"@id": f"{BASE}/my-doc-copy", "@type": "Document"},
            status=201,
        )
        result = cli.working_copy.checkout("/my-doc")
        assert "my-doc-copy" in result["@id"]

    @resp_mock.activate
    def test_checkin(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.PATCH,
            f"{BASE}/my-doc-copy/@workingcopy",
            json={"@id": f"{BASE}/my-doc", "review_state": "private"},
        )
        result = cli.working_copy.checkin("/my-doc-copy", message="Fixed spelling")
        assert "@id" in result

    @resp_mock.activate
    def test_cancel(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.DELETE,
            f"{BASE}/my-doc-copy/@workingcopy",
            status=204,
        )
        cli.working_copy.cancel("/my-doc-copy")

    @resp_mock.activate
    def test_info(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@workingcopy",
            json={"is_working_copy": False, "working_copy": None},
        )
        result = cli.working_copy.info("/my-doc")
        assert "is_working_copy" in result


# ---------------------------------------------------------------------------
# BlocksManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBlocksManager:
    @resp_mock.activate
    def test_get_slots(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@slots",
            json={"above-content": {"blocks": {}}},
        )
        result = cli.blocks.get_slots("/")
        assert "above-content" in result

    @resp_mock.activate
    def test_create_slot(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@slots/above-content",
            json={"@id": f"{BASE}/@slots/above-content"},
            status=201,
        )
        result = cli.blocks.create_slot(
            "/",
            "above-content",
            blocks={"uid-1": {"@type": "text", "value": "Hello"}},
        )
        assert "@id" in result

    @resp_mock.activate
    def test_delete_slot(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.DELETE,
            f"{BASE}/@slots/above-content",
            status=204,
        )
        cli.blocks.delete_slot("/", "above-content")

    @resp_mock.activate
    def test_available_block_types(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@available-blocks",
            json={"text": {"title": "Text"}, "image": {"title": "Image"}},
        )
        result = cli.blocks.available_block_types("/")
        assert "text" in result


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDatabaseManager:
    @resp_mock.activate
    def test_info(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@database",
            json={"db_size": 1024000, "num_connections": 2},
        )
        result = cli.database.info()
        assert "db_size" in result

    @resp_mock.activate
    def test_pack(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@pack-database",
            json={"message": "Database packed"},
        )
        result = cli.database.pack(days=7)
        assert "message" in result

    @resp_mock.activate
    def test_reindex(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@reindex",
            json={"message": "Catalog reindexed"},
        )
        result = cli.database.reindex()
        assert "message" in result

    @resp_mock.activate
    def test_link_integrity(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@linkintegrity",
            json={"breaches": []},
        )
        result = cli.database.link_integrity("/my-doc")
        assert "breaches" in result
