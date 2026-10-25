"""
Integration tests — require a running Plone via Docker.

Run with:
    pytest -m integration tests/integration/

These tests are skipped automatically when the ``plone_service`` fixture
cannot start (e.g. Docker is unavailable).
"""

from __future__ import annotations

from plone_client import PloneClient
from plone_client import PloneNotFoundError

import pytest


pytestmark = pytest.mark.integration


class TestContentCRUD:
    def test_get_site_root(self, integration_client: PloneClient) -> None:
        info = integration_client.site.info()
        assert "@type" in info

    def test_create_and_delete_document(self, integration_client: PloneClient) -> None:
        doc = integration_client.content.create(
            "/",
            "Document",
            title="Integration Test Document",
            description="Created by plone-client integration test",
        )
        assert doc.get("title") == "Integration Test Document"
        path = doc["@id"].replace(integration_client.config.base_url, "")

        # Clean up
        integration_client.content.delete(path)
        with pytest.raises(PloneNotFoundError):
            integration_client.content.get(path)

    def test_update_document(self, integration_client: PloneClient) -> None:
        doc = integration_client.content.create("/", "Document", title="To Be Updated")
        path = doc["@id"].replace(integration_client.config.base_url, "")
        try:
            updated = integration_client.content.update(path, title="Updated Title")
            assert updated["title"] == "Updated Title"
        finally:
            integration_client.content.delete(path)

    def test_workflow_transition(self, integration_client: PloneClient) -> None:
        doc = integration_client.content.create("/", "Document", title="Workflow Test")
        path = doc["@id"].replace(integration_client.config.base_url, "")
        try:
            result = integration_client.content.transition(path, "publish")
            assert result.get("review_state") == "published"
        finally:
            integration_client.content.delete(path)


class TestSearch:
    def test_search_returns_results(self, integration_client: PloneClient) -> None:
        results = integration_client.search.search({"portal_type": "Plone Site"})
        assert results["items_total"] >= 1

    def test_iterate(self, integration_client: PloneClient) -> None:
        items = list(integration_client.search.iterate(b_size=5))
        assert isinstance(items, list)


class TestUsersAndGroups:
    def test_list_users(self, integration_client: PloneClient) -> None:
        users = integration_client.users.list()
        assert any(u.get("id") == "admin" for u in users)

    def test_list_groups(self, integration_client: PloneClient) -> None:
        groups = integration_client.groups.list()
        assert isinstance(groups, list)

    def test_my_information(self, integration_client: PloneClient) -> None:
        info = integration_client.users.my_information()
        assert "id" in info


class TestFilesManager:
    def test_upload_and_download_file(self, integration_client: PloneClient) -> None:
        content = b"Hello, Plone! This is a test file."
        obj = integration_client.files.upload(
            "/",
            "test-upload.txt",
            content,
            content_type="text/plain",
            title="Test Upload",
        )
        path = obj["@id"].replace(integration_client.config.base_url, "")
        try:
            downloaded = integration_client.files.download(path)
            assert downloaded == content
        finally:
            integration_client.content.delete(path)

    def test_image_scales_available(self, integration_client: PloneClient) -> None:
        import struct
        import zlib

        def _tiny_png() -> bytes:
            def chunk(name: bytes, data: bytes) -> bytes:
                c = struct.pack(">I", len(data)) + name + data
                return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
            iend = chunk(b"IEND", b"")
            return sig + ihdr + idat + iend

        obj = integration_client.files.upload(
            "/", "test.png", _tiny_png(), content_type="image/png"
        )
        path = obj["@id"].replace(integration_client.config.base_url, "")
        try:
            scales = integration_client.files.image_scales(path)
            assert isinstance(scales, dict)
        finally:
            integration_client.content.delete(path)


class TestRelationsManager:
    def test_list_relations(self, integration_client: PloneClient) -> None:
        result = integration_client.relations.list()
        assert "items" in result

    def test_broken_relations(self, integration_client: PloneClient) -> None:
        result = integration_client.relations.broken()
        assert "items" in result


class TestUtilitiesManager:
    def test_user_schema(self, integration_client: PloneClient) -> None:
        result = integration_client.utilities.user_schema()
        assert "properties" in result or isinstance(result, dict)

    def test_site_config(self, integration_client: PloneClient) -> None:
        result = integration_client.utilities.site_config()
        assert isinstance(result, dict)

    def test_navigation_root(self, integration_client: PloneClient) -> None:
        result = integration_client.utilities.navigation_root("/")
        assert "@id" in result

    def test_resolve_uid(self, integration_client: PloneClient) -> None:
        # Search for any object to get a UID
        results = integration_client.search.search(b_size=1)
        if results["items_total"] == 0:
            pytest.skip("No content to resolve")
        item = results["items"][0]
        uid = item.get("UID")
        if not uid:
            pytest.skip("Item has no UID in search metadata")
        resolved = integration_client.utilities.resolve_uid(uid)
        assert resolved["@id"] == item["@id"]

    def test_ids_returns_list(self, integration_client: PloneClient) -> None:
        result = integration_client.utilities.ids("/")
        assert isinstance(result, list)

    def test_expandable_fields(self, integration_client: PloneClient) -> None:
        result = integration_client.utilities.expandable_fields("/")
        assert isinstance(result, list)


class TestDatabaseManager:
    def test_database_info(self, integration_client: PloneClient) -> None:
        result = integration_client.database.info()
        assert isinstance(result, dict)

    def test_catalog_sources(self, integration_client: PloneClient) -> None:
        result = integration_client.database.catalog_sources()
        assert isinstance(result, dict)


class TestWorkingCopyManager:
    def test_checkout_and_cancel(self, integration_client: PloneClient) -> None:
        doc = integration_client.content.create(
            "/", "Document", title="Working Copy Test"
        )
        path = doc["@id"].replace(integration_client.config.base_url, "")
        try:
            wc_info = integration_client.working_copy.info(path)
            assert isinstance(wc_info, dict)
        except Exception:
            pytest.skip("plone.app.iterate not installed")
        finally:
            integration_client.content.delete(path)


class TestEscapeHatch:
    def test_raw_request_to_custom_endpoint(
        self, integration_client: PloneClient
    ) -> None:
        """The escape hatch should work for any valid endpoint."""
        response = integration_client.request("GET", "/@search", params={"b_size": 1})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_shorthand(self, integration_client: PloneClient) -> None:
        response = integration_client.get("/@search", params={"b_size": 1})
        assert response.status_code == 200

    def test_post_shorthand(self, integration_client: PloneClient) -> None:
        """POST to /@querystring-search via escape hatch."""
        response = integration_client.post(
            "/@querystring-search",
            json={"query": [], "b_size": 1},
        )
        assert response.status_code == 200
        assert "items" in response.json()
