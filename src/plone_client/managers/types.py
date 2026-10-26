"""Content types, their schemas, and vocabularies."""

from .base import BaseManager
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any


#: A list of type ids; ``list`` itself is shadowed by the managers' method.
TypeIds = list[str]


class TypesManager(BaseManager):
    """Content types and their JSON schemas (``@types``)."""

    def list(self, ref: str = "/") -> list[dict[str, Any]]:
        """Content types, with whether they can be added in a folder.

        :param ref: Path or URL of the folder.
        :returns: ``@id``, ``title``, ``addable`` and ``immediately_addable``
            of each type.
        """
        return self._client.get(self._service(ref, "@types"))

    def addable(self, ref: str = "/") -> TypeIds:
        """Ids of the content types that can be added in a folder.

        :param ref: Path or URL of the folder.
        :returns: Type ids, such as ``Document``.
        """
        return [
            entry["@id"].rsplit("/", 1)[-1]
            for entry in self.list(ref)
            if entry.get("addable")
        ]

    def get(self, portal_type: str, *, ref: str = "/") -> dict[str, Any]:
        """JSON schema of a content type.

        :param portal_type: Type id, such as ``Document``.
        :param ref: Context, which affects some vocabularies in the schema.
        :returns: ``properties``, ``required``, ``fieldsets``…
        """
        return self._client.get(self._service(ref, f"@types/{portal_type}"))

    def get_field(self, portal_type: str, name: str) -> dict[str, Any]:
        """Schema of one field or fieldset of a content type.

        :param portal_type: Type id.
        :param name: Field or fieldset name.
        :returns: Its schema.
        """
        return self._client.get(f"/@types/{portal_type}/{name}")

    def create_field(self, portal_type: str, data: Mapping[str, Any]) -> dict[str, Any]:
        """Add a field (or, with ``fieldset`` data, a fieldset) to a type.

        Only for types whose schema is stored in the site, not in code.

        :param portal_type: Type id.
        :param data: ``factory``, ``title``, ``description``, ``required``…
        :returns: The new field.
        """
        return self._client.post(f"/@types/{portal_type}", dict(data))

    def update(
        self, portal_type: str, data: Mapping[str, Any], *, name: str | None = None
    ) -> None:
        """Change a type's schema, or one of its fields or fieldsets.

        :param portal_type: Type id.
        :param data: Changes to apply.
        :param name: Field or fieldset name; the whole schema when missing.
        """
        path = f"/@types/{portal_type}/{name}" if name else f"/@types/{portal_type}"
        self._client.patch(path, dict(data))

    def replace(self, portal_type: str, schema: Mapping[str, Any]) -> None:
        """Replace a type's schema.

        :param portal_type: Type id.
        :param schema: The full schema.
        """
        self._client.put(f"/@types/{portal_type}", dict(schema))

    def delete_field(self, portal_type: str, name: str) -> None:
        """Remove a field or fieldset from a type.

        :param portal_type: Type id.
        :param name: Field or fieldset name.
        """
        self._client.delete(f"/@types/{portal_type}/{name}")


class VocabulariesManager(BaseManager):
    """Vocabularies and field sources."""

    def list(self, ref: str = "/") -> list[dict[str, Any]]:
        """Named vocabularies registered on the site.

        :param ref: Context of the vocabularies.
        :returns: ``@id`` and ``title`` of each one.
        """
        return self._client.get(self._service(ref, "@vocabularies"))

    def get(
        self,
        name: str,
        *,
        ref: str = "/",
        title: str | None = None,
        token: str | Iterable[str] | None = None,
        sort_on: str | None = None,
        sort_order: str | None = None,
        b_size: int | None = None,
        b_start: int | None = None,
    ) -> dict[str, Any]:
        """Terms of a vocabulary, a page at a time.

        :param name: Vocabulary name, such as ``plone.app.vocabularies.Keywords``.
        :param ref: Context of the vocabulary.
        :param title: Only terms whose title contains this text.
        :param token: Only the term with this token, or with these tokens.
        :param sort_on: ``token`` or ``title``.
        :param sort_order: ``ascending`` or ``descending``.
        :param b_size: Terms per page; ``-1`` returns them all.
        :param b_start: Offset of the page.
        :returns: ``items`` (``token`` and ``title``) and ``items_total``.
        """
        params: dict[str, Any] = {
            "title": title,
            "sort_on": sort_on,
            "sort_order": sort_order,
            "b_size": b_size,
            "b_start": b_start,
        }
        if isinstance(token, str):
            params["token"] = token
        elif token is not None:
            params["tokens"] = list(token)
        return self._client.get(self._service(ref, f"@vocabularies/{name}"), **params)

    def iter(
        self, name: str, *, ref: str = "/", title: str | None = None
    ) -> Iterator[dict[str, Any]]:
        """Every term of a vocabulary.

        :param name: Vocabulary name.
        :param ref: Context of the vocabulary.
        :param title: Only terms whose title contains this text.
        :returns: Each term.
        """
        return self._client.iter_items(
            self._service(ref, f"@vocabularies/{name}"),
            {"title": title, "b_size": 100},
        )

    def source(self, ref: str, field: str) -> dict[str, Any]:
        """Terms of the source of a field (``@sources``).

        :param ref: Path or URL of an item with the field.
        :param field: Field name.
        :returns: ``items`` and ``items_total``.
        """
        return self._client.get(self._service(ref, f"@sources/{field}"))

    def querysource(self, ref: str, field: str, query: str) -> dict[str, Any]:
        """Terms of a query source matching a text (``@querysources``).

        :param ref: Path or URL of an item with the field.
        :param field: Field name.
        :param query: Text to search for.
        :returns: ``items`` and ``items_total``.
        """
        return self._client.get(
            self._service(ref, f"@querysources/{field}"), query=query
        )
