"""Content: read, create, update, delete, copy, move, order and lock items."""

from ..exceptions import PloneNotFoundError
from ..utils import uid_from_ref
from .base import BaseManager
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any
from typing import Literal


def _sources(refs: str | Iterable[str]) -> list[str]:
    """Normalize one or more references for ``@copy`` and ``@move``.

    :param refs: A reference or several.
    :returns: A list of references.
    """
    return [refs] if isinstance(refs, str) else list(refs)


class ContentManager(BaseManager):
    """Content items, through the content endpoints of ``plone.restapi``.

    Every method takes the path of an item, or its URL as found in ``@id``.
    """

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def get(
        self,
        ref: str = "/",
        *,
        expand: str | Iterable[str] | None = None,
        fullobjects: bool = False,
        include_items: bool | None = None,
        version: str | int | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Serialization of an item.

        :param ref: Path or URL of the item; also ``uid:<UID>``.
        :param expand: Components to expand inline (``breadcrumbs``,
            ``navigation``, ``translations``…).
        :param fullobjects: Serialize the contained items in full.
        :param include_items: ``False`` leaves the contained items out.
        :param version: Version of the item to return, from ``@history``.
        :param params: Other query parameters.
        :returns: The item.
        """
        if not isinstance(expand, str) and expand is not None:
            expand = ",".join(expand)
        query: dict[str, Any] = {
            "expand": expand or None,
            "fullobjects": 1 if fullobjects else None,
            "include_items": include_items,
            "version": version,
            **params,
        }
        return self._client.get(self.resolve(ref), **query)

    def find_by_uid(self, uid: str) -> dict[str, Any]:
        """Catalog entry of the item with a UID.

        :param uid: The UID.
        :returns: The search result, with ``@id``, ``@type`` and ``title``.
        :raises PloneNotFoundError: If no item has this UID.
        """
        found = self._client.get("/@search", UID=uid)
        if not found.get("items"):
            raise PloneNotFoundError(
                f"No item with UID {uid}",
                status_code=404,
                error_type="NotFound",
                method="GET",
                url=self._client.api_url("/@search"),
            )
        return found["items"][0]

    def resolve(self, ref: str) -> str:
        """Site path for a reference.

        Plain paths and URLs are only normalized. ``uid:<UID>`` and
        ``resolveuid`` links are looked up in the catalog.

        :param ref: Path, URL, ``uid:<UID>`` or ``resolveuid`` link.
        :returns: The site path.
        :raises PloneNotFoundError: If the UID is not found.
        """
        uid = uid_from_ref(ref)
        if uid:
            return self._client.path(self.find_by_uid(uid)["@id"])
        return self._client.path(ref)

    def exists(self, ref: str) -> bool:
        """Say whether there is an item at a path.

        :param ref: Path or URL of the item.
        :returns: ``True`` if it exists.
        """
        return self._client.exists(ref)

    def children(
        self,
        ref: str = "/",
        *,
        portal_type: str | Iterable[str] | None = None,
        metadata_fields: str | Iterable[str] | None = None,
        limit: int | None = None,
        b_size: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Items directly inside a folder, in the folder's order.

        Uses ``@search`` on the folder, so each item is a catalog entry
        rather than a full serialization.

        :param ref: Path or URL of the folder.
        :param portal_type: Only items of these types.
        :param metadata_fields: Extra catalog metadata to return
            (``_all`` for every column).
        :param limit: Stop after this many items.
        :param b_size: Items fetched per request.
        :returns: Each item.
        """
        params = {
            "path.depth": 1,
            "sort_on": "getObjPositionInParent",
            "portal_type": portal_type,
            "metadata_fields": metadata_fields,
            "b_size": b_size,
        }
        return self._client.iter_items(
            self._service(ref, "@search"), params, limit=limit
        )

    # ------------------------------------------------------------------
    # Changing
    # ------------------------------------------------------------------

    def create(
        self,
        parent: str,
        portal_type: str,
        data: Mapping[str, Any] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """Create an item inside a folder.

        Read the ``@id`` of the result rather than assuming it: Plone may
        change the id that was asked for.

        :param parent: Path or URL of the folder.
        :param portal_type: Content type, such as ``Document``.
        :param data: Field values; also ``id``, and ``UID`` (needs the
            *Manage portal* permission).
        :param fields: More field values, merged over ``data``.
        :returns: The new item.
        :raises PloneBadRequestError: If the id is in use, the type is not
            allowed in the folder, or a field is invalid.
        """
        payload = {"@type": portal_type, **(data or {}), **fields}
        return self._client.post(self.resolve(parent), payload)

    def update(
        self,
        ref: str,
        data: Mapping[str, Any] | None = None,
        *,
        lock_token: str | None = None,
        representation: bool = True,
        **fields: Any,
    ) -> dict[str, Any] | None:
        """Change fields of an item (``PATCH``).

        :param ref: Path or URL of the item.
        :param data: Field values.
        :param lock_token: Token of a lock held on the item.
        :param representation: Ask the site to return the changed item.
        :param fields: More field values, merged over ``data``.
        :returns: The changed item, or ``None`` with ``representation=False``.
        """
        headers = {}
        if representation:
            headers["Prefer"] = "return=representation"
        if lock_token:
            headers["Lock-Token"] = lock_token
        payload = {**(data or {}), **fields}
        return self._client.patch(self.resolve(ref), payload, headers=headers)

    def delete(self, ref: str) -> None:
        """Delete an item.

        :param ref: Path or URL of the item.
        :raises PloneBadRequestError: If link integrity forbids the deletion.
        """
        self._client.delete(self.resolve(ref))

    def copy(self, source: str | Iterable[str], target: str) -> list[dict[str, Any]]:
        """Copy items into a folder.

        :param source: Path, URL or UID of an item, or several.
        :param target: Path or URL of the folder.
        :returns: One ``{"source", "target"}`` entry per item.
        """
        return self._client.post(
            self._service(target, "@copy"), {"source": _sources(source)}
        )

    def move(self, source: str | Iterable[str], target: str) -> list[dict[str, Any]]:
        """Move items into a folder.

        :param source: Path, URL or UID of an item, or several.
        :param target: Path or URL of the folder.
        :returns: One ``{"source", "target"}`` entry per item.
        """
        return self._client.post(
            self._service(target, "@move"), {"source": _sources(source)}
        )

    def order(
        self,
        folder: str,
        obj_id: str,
        delta: int | Literal["top", "bottom"],
        *,
        subset_ids: Iterable[str] | None = None,
    ) -> None:
        """Move an item within its folder.

        :param folder: Path or URL of the folder.
        :param obj_id: Id of the item to move.
        :param delta: Positions to move (negative moves up), ``top`` or
            ``bottom``.
        :param subset_ids: Ids of the items the client knows about, in their
            current order; the site refuses the change if they are out of date.
        """
        ordering: dict[str, Any] = {"obj_id": obj_id, "delta": delta}
        if subset_ids is not None:
            ordering["subset_ids"] = list(subset_ids)
        self._client.patch(self.resolve(folder), {"ordering": ordering})

    def sort(
        self,
        folder: str,
        on: str,
        order: Literal["ascending", "descending"] = "ascending",
    ) -> None:
        """Sort the items of a folder by an index, once.

        :param folder: Path or URL of the folder.
        :param on: Catalog index to sort on, such as ``modified``.
        :param order: ``ascending`` or ``descending``.
        """
        self._client.patch(self.resolve(folder), {"sort": {"on": on, "order": order}})

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    def lock(
        self, ref: str, *, stealable: bool = True, timeout: int | None = None
    ) -> dict[str, Any]:
        """Lock an item.

        :param ref: Path or URL of the item.
        :param stealable: Let other users break the lock.
        :param timeout: Seconds the lock lasts.
        :returns: Lock information, with the ``token`` to send in updates.
        """
        data: dict[str, Any] = {"stealable": stealable}
        if timeout is not None:
            data["timeout"] = timeout
        return self._client.post(self._service(ref, "@lock"), data)

    def unlock(self, ref: str, *, force: bool = False) -> dict[str, Any]:
        """Remove the lock of an item.

        :param ref: Path or URL of the item.
        :param force: Remove a lock held by another user.
        :returns: Lock information.
        """
        data = {"force": True} if force else None
        return self._client.delete(self._service(ref, "@lock"), data)

    def refresh_lock(self, ref: str) -> dict[str, Any]:
        """Extend the lock of an item.

        :param ref: Path or URL of the item.
        :returns: Lock information.
        """
        return self._client.patch(self._service(ref, "@lock"))

    def lock_info(self, ref: str) -> dict[str, Any]:
        """Lock information of an item.

        :param ref: Path or URL of the item.
        :returns: ``locked``, ``stealable`` and, when locked, the owner.
        """
        return self._client.get(self._service(ref, "@lock"))

    # ------------------------------------------------------------------
    # Link integrity
    # ------------------------------------------------------------------

    def link_integrity(self, uids: str | Iterable[str]) -> list[dict[str, Any]]:
        """Items that link to the given items.

        Check this before deleting content.

        :param uids: UID of an item, or several.
        :returns: One entry per item, with its ``breaches``.
        """
        return self._client.get("/@linkintegrity", uids=_sources(uids))
