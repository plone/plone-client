"""Files and images: upload, replace and download."""

from ..exceptions import PloneClientError
from .base import BaseManager
from pathlib import Path
from typing import Any

import base64
import mimetypes


#: Chunk size for TUS uploads: 4 MiB.
TUS_CHUNK_SIZE = 4 * 1024 * 1024
TUS_VERSION = "1.0.0"

FileSource = str | Path | bytes


def _read(
    source: FileSource, filename: str | None, content_type: str | None
) -> tuple[bytes, str, str]:
    """Bytes, file name and content type of a file.

    :param source: Path of the file, or its bytes.
    :param filename: File name; required when ``source`` is bytes.
    :param content_type: Content type; guessed from the file name if missing.
    :returns: The data, the file name and the content type.
    :raises ValueError: If bytes are given without a file name.
    """
    if isinstance(source, bytes):
        if not filename:
            raise ValueError("A filename is required when uploading bytes")
        data = source
    else:
        path = Path(source)
        data = path.read_bytes()
        filename = filename or path.name
    content_type = (
        content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )
    return data, filename, content_type


def file_data(
    source: FileSource,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, str]:
    """Value of a file or image field, as ``plone.restapi`` reads it.

    :param source: Path of the file, or its bytes.
    :param filename: File name; required when ``source`` is bytes.
    :param content_type: Content type; guessed from the file name if missing.
    :returns: ``data`` (base64), ``encoding``, ``filename`` and ``content-type``.
    """
    data, filename, content_type = _read(source, filename, content_type)
    return {
        "data": base64.b64encode(data).decode("ascii"),
        "encoding": "base64",
        "filename": filename,
        "content-type": content_type,
    }


def _defaults(
    content_type: str, portal_type: str | None, field: str | None
) -> tuple[str, str]:
    """Content type and field to store a file in.

    :param content_type: Content type of the file.
    :param portal_type: Content type asked for, if any.
    :param field: Field asked for, if any.
    :returns: ``Image`` and ``image`` for images, ``File`` and ``file``
        otherwise, unless given.
    """
    portal_type = portal_type or (
        "Image" if content_type.startswith("image/") else "File"
    )
    field = field or ("image" if portal_type == "Image" else "file")
    return portal_type, field


def _tus_metadata(values: dict[str, str]) -> str:
    """``Upload-Metadata`` header for a TUS upload.

    :param values: Metadata, such as ``filename`` and ``content-type``.
    :returns: Comma separated ``key base64(value)`` pairs.
    """
    return ",".join(
        f"{key} {base64.b64encode(value.encode()).decode('ascii')}"
        for key, value in values.items()
    )


class FilesManager(BaseManager):
    """Files and images stored in content items."""

    def upload(
        self,
        parent: str,
        source: FileSource,
        *,
        portal_type: str | None = None,
        field: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """Create a ``File`` or ``Image`` from a file, in one request.

        The file travels base64 encoded inside the JSON body, which is
        simple and works on every site; for large files use :meth:`tus_upload`.

        :param parent: Path or URL of the folder.
        :param source: Path of the file, or its bytes.
        :param portal_type: Content type; ``Image`` for images and ``File``
            for anything else by default.
        :param field: Field that holds the file; ``image`` for ``Image`` and
            ``file`` otherwise by default.
        :param filename: File name; required when ``source`` is bytes.
        :param content_type: Content type; guessed from the file name if missing.
        :param fields: Other field values, such as ``id`` or ``title``.
        :returns: The new item.
        """
        value = file_data(source, filename=filename, content_type=content_type)
        portal_type, field = _defaults(value["content-type"], portal_type, field)
        data = {"title": value["filename"], **fields, field: value}
        return self._client.content.create(parent, portal_type, data)

    def replace(
        self,
        ref: str,
        source: FileSource,
        *,
        field: str = "file",
        filename: str | None = None,
        content_type: str | None = None,
    ) -> None:
        """Replace the file stored in a field of an item.

        :param ref: Path or URL of the item.
        :param source: Path of the file, or its bytes.
        :param field: Field that holds the file (``image`` for images).
        :param filename: File name; required when ``source`` is bytes.
        :param content_type: Content type; guessed from the file name if missing.
        """
        value = file_data(source, filename=filename, content_type=content_type)
        self._client.content.update(ref, {field: value}, representation=False)

    def download(self, ref: str, *, field: str = "file") -> bytes:
        """Contents of a file field (``@@download``).

        :param ref: Path or URL of the item.
        :param field: Field that holds the file (``image`` for images).
        :returns: The file contents.
        """
        response = self._client.request(
            "GET", self._service(ref, f"@@download/{field}")
        )
        return response.content

    def image_scale(
        self, ref: str, *, field: str = "image", scale: str = "preview"
    ) -> bytes:
        """Contents of an image scale (``@@images``).

        :param ref: Path or URL of the item.
        :param field: Field that holds the image.
        :param scale: Scale name, such as ``thumb``, ``preview`` or ``large``.
        :returns: The scaled image.
        """
        response = self._client.request(
            "GET", self._service(ref, f"@@images/{field}/{scale}")
        )
        return response.content

    def _tus(
        self,
        service: str,
        data: bytes,
        metadata: dict[str, str],
        chunk_size: int,
    ) -> str:
        """Send a file with the TUS protocol.

        :param service: Path of ``@tus-upload`` or ``@tus-replace``.
        :param data: File contents.
        :param metadata: TUS metadata.
        :param chunk_size: Bytes sent per request.
        :returns: URL of the item, from the last ``Location`` header.
        """
        response = self._client.request(
            "POST",
            service,
            headers={
                "Tus-Resumable": TUS_VERSION,
                "Upload-Length": str(len(data)),
                "Upload-Metadata": _tus_metadata(metadata),
            },
        )
        upload_url = response.headers.get("Location", "")
        if self._client.dry_run:
            return upload_url
        offset = 0
        location = ""
        while offset < len(data):
            chunk = data[offset : offset + chunk_size]
            response = self._client.request(
                "PATCH",
                upload_url,
                content=chunk,
                headers={
                    "Tus-Resumable": TUS_VERSION,
                    "Upload-Offset": str(offset),
                    "Content-Type": "application/offset+octet-stream",
                },
            )
            offset = int(response.headers.get("Upload-Offset", offset + len(chunk)))
            location = response.headers.get("Location", location)
        if not location:
            # plone.restapi answers 204 even when it fails to store the file
            raise PloneClientError(
                f"The upload to {service} finished, but the site did not store "
                "the file; check the content type and field"
            )
        return location

    def tus_upload(
        self,
        parent: str,
        source: FileSource,
        *,
        portal_type: str | None = None,
        field: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
        chunk_size: int = TUS_CHUNK_SIZE,
    ) -> str:
        """Create an item from a large file, sent in chunks (``@tus-upload``).

        :param parent: Path or URL of the folder.
        :param source: Path of the file, or its bytes.
        :param portal_type: Content type; ``Image`` for images and ``File``
            for anything else by default.
        :param field: Field that holds the file; ``image`` for ``Image`` and
            ``file`` otherwise by default.
        :param filename: File name; required when ``source`` is bytes.
        :param content_type: Content type; guessed from the file name if missing.
        :param chunk_size: Bytes sent per request.
        :returns: URL of the new item.
        """
        data, filename, content_type = _read(source, filename, content_type)
        portal_type, field = _defaults(content_type, portal_type, field)
        metadata = {
            "filename": filename,
            "content-type": content_type,
            "@type": portal_type,
            "fieldname": field,
        }
        return self._tus(
            self._service(parent, "@tus-upload"), data, metadata, chunk_size
        )

    def tus_replace(
        self,
        ref: str,
        source: FileSource,
        *,
        field: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
        chunk_size: int = TUS_CHUNK_SIZE,
    ) -> str:
        """Replace the file of an item with a large file (``@tus-replace``).

        :param ref: Path or URL of the item.
        :param source: Path of the file, or its bytes.
        :param field: Field that holds the file.
        :param filename: File name; required when ``source`` is bytes.
        :param content_type: Content type; guessed from the file name if missing.
        :param chunk_size: Bytes sent per request.
        :returns: URL of the item.
        """
        data, filename, content_type = _read(source, filename, content_type)
        metadata = {"filename": filename, "content-type": content_type}
        if field:
            metadata["fieldname"] = field
        return self._tus(self._service(ref, "@tus-replace"), data, metadata, chunk_size)
