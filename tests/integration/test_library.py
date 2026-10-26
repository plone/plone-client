from plone_client import blocks
from plone_client import PloneBadRequestError
from plone_client import PloneNotFoundError

import pytest


pytestmark = pytest.mark.integration


def test_site_information(plone):
    assert plone.system.site()["plone.site_title"]
    assert plone.system.system()["plone_version"].startswith("6.")


def test_content_life_cycle(plone, folder):
    page = plone.content.create(
        folder,
        "Document",
        title="Page",
        **blocks.build(blocks.title(), blocks.text("Hi")),
    )
    path = plone.path(page["@id"])
    assert page["@id"] == plone.site_url(path)
    updated = plone.content.update(path, title="Changed")
    assert updated["title"] == "Changed"
    entry = plone.workflow.transition(path, "publish", comment="test")
    assert entry["review_state"] == "published"
    assert plone.content.get(f"uid:{page['UID']}")["@id"] == page["@id"]
    plone.content.delete(path)
    assert plone.exists(path) is False


def test_duplicate_id_is_a_bad_request(plone, folder):
    plone.content.create(folder, "Document", id="same", title="Same")
    with pytest.raises(PloneBadRequestError, match="already in use"):
        plone.content.create(folder, "Document", id="same", title="Same")


def test_not_found(plone):
    with pytest.raises(PloneNotFoundError):
        plone.content.get("/does-not-exist")


def test_children_order_copy_move(plone, folder):
    for title in ("One", "Two", "Three"):
        plone.content.create(folder, "Document", title=title)
    plone.content.order(folder, "three", "top")
    ids = [
        plone.path(c["@id"]).rsplit("/", 1)[-1] for c in plone.content.children(folder)
    ]
    assert ids == ["three", "one", "two"]
    plone.content.copy(f"{folder}/one", f"{folder}/two")
    plone.content.move(f"{folder}/two/one", f"{folder}/three")
    assert plone.exists(f"{folder}/three/one")


def test_search_batches(plone, folder):
    for index in range(5):
        plone.content.create(folder, "Document", title=f"Item {index}")
    found = list(plone.search.iter(folder, depth=1, b_size=2))
    assert len(found) == 5
    assert plone.search.count(folder, depth=1) == 5


def test_files(plone, folder):
    item = plone.files.upload(folder, b"hello", filename="hello.txt")
    assert item["@type"] == "File"
    assert plone.files.download(item["@id"]) == b"hello"
    location = plone.files.tus_upload(
        folder, b"tus " * 1000, filename="big.txt", chunk_size=1000
    )
    assert plone.files.download(location) == b"tus " * 1000


def test_lock(plone, folder):
    lock = plone.content.lock(folder)
    assert lock["locked"] is True
    assert plone.content.unlock(folder)["locked"] is False


def test_users_and_groups(plone):
    plone.users.create("integration", email="it@example.com", password="it-Pass-1234")
    try:
        plone.groups.add_members("Reviewers", "integration")
        assert "integration" in plone.groups.get("Reviewers")["members"]["items"]
    finally:
        plone.users.delete("integration", delete_memberareas=False)
