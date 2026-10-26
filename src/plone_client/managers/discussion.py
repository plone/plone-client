"""Comments, translations, aliases and relations."""

from .base import BaseManager
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any


class CommentsManager(BaseManager):
    """Comments on an item (``@comments``).

    Comments must be enabled on the site and on the content type.
    """

    def list(self, ref: str, *, limit: int | None = None) -> Iterator[dict[str, Any]]:
        """Comments of an item.

        :param ref: Path or URL of the item.
        :param limit: Stop after this many comments.
        :returns: Each comment.
        """
        return self._client.iter_items(self._service(ref, "@comments"), limit=limit)

    def add(self, ref: str, text: str, *, reply_to: str | None = None) -> None:
        """Add a comment, or a reply to a comment.

        :param ref: Path or URL of the item.
        :param text: Text of the comment.
        :param reply_to: Id of the comment to reply to.
        """
        service = f"@comments/{reply_to}" if reply_to else "@comments"
        self._client.post(self._service(ref, service), {"text": text})

    def update(self, ref: str, comment_id: str, text: str) -> None:
        """Change the text of a comment.

        :param ref: Path or URL of the item.
        :param comment_id: Id of the comment.
        :param text: New text.
        """
        self._client.patch(
            self._service(ref, f"@comments/{comment_id}"), {"text": text}
        )

    def delete(self, ref: str, comment_id: str) -> None:
        """Delete a comment.

        :param ref: Path or URL of the item.
        :param comment_id: Id of the comment.
        """
        self._client.delete(self._service(ref, f"@comments/{comment_id}"))


class TranslationsManager(BaseManager):
    """Translations of an item (``@translations``).

    Needs ``plone.app.multilingual`` installed on the site.
    """

    def get(self, ref: str) -> dict[str, Any]:
        """Translations linked to an item.

        :param ref: Path or URL of the item.
        :returns: ``items`` with the ``@id`` and ``language`` of each translation.
        """
        return self._client.get(self._service(ref, "@translations"))

    def link(self, ref: str, translation: str) -> dict[str, Any]:
        """Link an existing item as a translation.

        :param ref: Path or URL of the item.
        :param translation: Path, URL or UID of the translation.
        :returns: The linked translation.
        """
        return self._client.post(
            self._service(ref, "@translations"), {"id": translation}
        )

    def unlink(self, ref: str, language: str) -> None:
        """Remove the link to the translation in a language.

        :param ref: Path or URL of the item.
        :param language: Language code of the translation.
        """
        self._client.delete(self._service(ref, "@translations"), {"language": language})

    def locate(self, ref: str, language: str) -> dict[str, Any]:
        """Where a translation into a language should be created.

        :param ref: Path or URL of the item.
        :param language: Language code of the new translation.
        :returns: ``@id`` of the folder for the translation.
        """
        return self._client.get(
            self._service(ref, "@translation-locator"), target_language=language
        )


class AliasesManager(BaseManager):
    """URL aliases and redirections (``@aliases``)."""

    def list(self, ref: str = "/", **params: Any) -> dict[str, Any]:
        """Aliases of an item, or every redirection of the site.

        :param ref: Path or URL of the item; the site root lists them all.
        :param params: Filters accepted on the site root, such as ``query``,
            ``manual``, ``start``, ``end``, ``b_size``.
        :returns: ``items`` and ``items_total``.
        """
        return self._client.get(self._service(ref, "@aliases"), **params)

    def add(self, ref: str, aliases: str | Iterable[str]) -> None:
        """Add aliases to an item.

        :param ref: Path or URL of the item.
        :param aliases: Old path, or several, that should redirect to the item.
        """
        paths = [aliases] if isinstance(aliases, str) else list(aliases)
        self._client.post(
            self._service(ref, "@aliases"), {"items": [{"path": p} for p in paths]}
        )

    def add_redirects(self, redirects: Iterable[Mapping[str, Any]]) -> None:
        """Add redirections on the site root.

        :param redirects: Entries with ``path`` (the old path),
            ``redirect-to`` (the target) and, optionally, ``datetime``.
        """
        self._client.post("/@aliases", {"items": [dict(r) for r in redirects]})

    def remove(self, ref: str, aliases: str | Iterable[str]) -> None:
        """Remove aliases.

        :param ref: Path or URL of the item, or the site root.
        :param aliases: Alias path, or several.
        """
        paths = [aliases] if isinstance(aliases, str) else list(aliases)
        self._client.delete(
            self._service(ref, "@aliases"), {"items": [{"path": p} for p in paths]}
        )


class RelationsManager(BaseManager):
    """Relations between items (``@relations``)."""

    def stats(self) -> dict[str, Any]:
        """Number of relations of each kind.

        :returns: ``stats`` and ``broken`` counts.
        """
        return self._client.get("/@relations")

    def list(
        self,
        *,
        source: str | None = None,
        target: str | None = None,
        relation: str | None = None,
        query_source: str | None = None,
        query_target: str | None = None,
        only_broken: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Relations matching a filter.

        :param source: Path or UID of the source item.
        :param target: Path or UID of the target item.
        :param relation: Relation name, such as ``relatedItems``.
        :param query_source: Text the source title must match.
        :param query_target: Text the target title must match.
        :param only_broken: Only relations whose target is gone.
        :param limit: Maximum number of relations returned.
        :returns: ``relations`` by name, with ``items`` and ``items_total``.
        """
        return self._client.get(
            "/@relations",
            source=source,
            target=target,
            relation=relation,
            query_source=query_source,
            query_target=query_target,
            onlyBroken=True if only_broken else None,
            max=limit,
        )

    def create(self, relations: Iterable[Mapping[str, str]]) -> None:
        """Create relations.

        :param relations: Entries with ``source``, ``target`` (paths or UIDs)
            and ``relation``.
        """
        self._client.post("/@relations", {"items": [dict(r) for r in relations]})

    def delete(
        self,
        relations: Iterable[Mapping[str, str]] | None = None,
        *,
        source: str | None = None,
        target: str | None = None,
        relation: str | None = None,
    ) -> None:
        """Delete relations, listed one by one or by filter.

        :param relations: Entries with ``source``, ``target`` and ``relation``.
        :param source: Delete every relation from this item.
        :param target: Delete every relation to this item.
        :param relation: Delete every relation with this name.
        """
        if relations is not None:
            data: dict[str, Any] = {"items": [dict(r) for r in relations]}
        else:
            data = {
                key: value
                for key, value in (
                    ("source", source),
                    ("target", target),
                    ("relation", relation),
                )
                if value
            }
        if not data:
            raise ValueError("Give relations, or a source, target or relation")
        self._client.delete("/@relations", data)

    def rebuild(self, *, flush: bool = False) -> None:
        """Rebuild the relation catalog.

        :param flush: Empty the catalog first, which also refreshes intids.
        """
        self._client.post("/@relations/rebuild", {"flush": 1} if flush else None)
