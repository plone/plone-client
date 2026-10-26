from plone_client import utils

import pytest


UID = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    "ref,expected",
    [
        (f"uid:{UID}", UID),
        (f"../resolveuid/{UID}", UID),
        (f"resolveuid/{UID}", UID),
        (f"https://example.org/resolveuid/{UID}", UID),
        (f"https://example.org/resolveuid/{UID}/@@download/file", UID),
        (f"../resolveuid/{UID}#section", UID),
        ("/news/item", ""),
        ("https://example.org/news", ""),
        (f"/resolveuid/{UID}extra", ""),
        (UID, ""),
    ],
)
def test_uid_from_ref(ref, expected):
    assert utils.uid_from_ref(ref) == expected


def test_uid_from_ref_rejects_invalid_uid():
    with pytest.raises(ValueError, match="Not a valid UID"):
        utils.uid_from_ref("uid:not-a-uid")


@pytest.mark.parametrize(
    "suffix,expected",
    [
        ("", f"../resolveuid/{UID}"),
        ("#top", f"../resolveuid/{UID}#top"),
        ("/@@download/file", f"../resolveuid/{UID}/@@download/file"),
    ],
)
def test_resolveuid_url(suffix, expected):
    assert utils.resolveuid_url(UID, suffix) == expected
