from plone_client import blocks
from plone_client import operations
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


def _stored(plone, path):
    item = plone.content.get(path, include_items=False)
    return item["blocks"], item["blocks_layout"]["items"]


def test_block_operations(plone, folder):
    page = blocks.build(blocks.title(), blocks.description(), blocks.text("First"))
    plone.content.update(folder, page)
    title, description, first = page["blocks_layout"]["items"]

    grid = {"@type": "gridBlock", "blocks": [{"@type": "teaser", "href": folder}]}
    result = operations.add_blocks(plone, folder, [grid], after=description)
    (grid_id,) = result.changed[0]["added"]
    found, order = _stored(plone, folder)
    assert order == [title, description, grid_id, first]
    (teaser_id,) = found[grid_id]["blocks_layout"]["items"]
    assert found[grid_id]["blocks"][teaser_id]["href"][0]["@id"].endswith(folder)

    operations.update_block(plone, folder, teaser_id, {"overwrite": True})
    found, _ = _stored(plone, folder)
    assert found[grid_id]["blocks"][teaser_id]["overwrite"] is True

    operations.remove_blocks(plone, folder, [first])
    found, order = _stored(plone, folder)
    assert order == [title, description, grid_id]
    assert first not in found

    result = operations.set_blocks(plone, folder, [{"@type": "slate"}])
    (slate,) = result.changed[0]["added"]
    found, order = _stored(plone, folder)
    assert order == [title, description, slate]
    assert set(found) == {title, description, slate}
