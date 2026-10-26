"""Small helpers shared by the library and the command line."""

import re


#: A Plone UID: 32 lowercase hexadecimal characters.
UID_RE = re.compile(r"^[0-9a-f]{32}$")
_RESOLVEUID_RE = re.compile(r"(?:^|/)resolveuid/([0-9a-f]{32})(?=$|[/?#])")


def uid_from_ref(ref: str) -> str:
    """UID named by a reference, if the reference names one.

    Two forms name a UID: ``uid:<UID>`` and a ``resolveuid`` link, the way
    Volto stores internal links (``../resolveuid/<UID>``,
    ``https://example.org/resolveuid/<UID>/@@download/file``).

    :param ref: A path, URL or UID reference.
    :returns: The UID, or an empty string when ``ref`` is a plain path or URL.
    """
    ref = ref.strip()
    if ref.startswith("uid:"):
        uid = ref[4:]
        if not UID_RE.match(uid):
            raise ValueError(f"Not a valid UID: {uid!r}")
        return uid
    match = _RESOLVEUID_RE.search(ref)
    return match.group(1) if match else ""


def resolveuid_url(uid: str, suffix: str = "") -> str:
    """Link to an item by UID, in the form Volto stores in blocks.

    :param uid: UID of the item.
    :param suffix: Text appended to the link, such as ``#section`` or
        ``/@@download/file``.
    :returns: ``../resolveuid/<UID><suffix>``.
    """
    return f"../resolveuid/{uid}{suffix}"
