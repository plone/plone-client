"""
Files & attachments manager.

Covers:
- Uploading files via ``@upload`` (TUS protocol support in Plone 6)
- Downloading file/image fields
- ``@images`` sub-resource (scaled image variants)
- ``@download`` sub-resource
"""

from __future__ import annotations

from .base import BaseManager
from pathlib import Path
from typing import Any
from typing import IO
from typing import TypeAlias

import mimetypes
import os


_FileLike: TypeAlias = IO[bytes] | bytes | Path | str


def _open_file(source: _FileLike) -> tuple[str, IO[bytes], str]:
    """
    Normalise *source* into ``(filename, file_obj, content_type)``.

    Accepts a file-like object, bytes, a :class:`pathlib.Path`, or a
    string path.

    :param source: The file data to normalise.
    :type source: IO[bytes] or bytes or pathlib.Path or str
    :returns: Tuple of ``(filename, file_obj, content_type)``.
    :rtype: tuple[str, IO[bytes], str]
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        return path.name, open(path, "rb"), mime

    if isinstance(source, bytes):
        import io

        return "upload", io.BytesIO(source), "application/octet-stream"

    # file-like: try to infer name and mime
    name = getattr(source, "name", "upload")
    name = os.path.basename(name) if name else "upload"
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return name, source, mime  # type: ignore[return-value]


class FilesManager(BaseManager):
    """
    Upload and download files attached to Plone content objects.

    >>> files_mgr.upload("/documents", "myreport.pdf", open("report.pdf", "rb"))
    >>> image_url = files_mgr.image_scale("/news/article", "image", "preview")
    """

    # ------------------------------------------------------------------
    # Upload (classic multipart — works on all Plone versions)
    # ------------------------------------------------------------------

    def upload(
        self,
        container_path: str,
        filename: str,
        source: _FileLike,
        *,
        field: str = "file",
        content_type: str | None = None,
        title: str = "",
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """
        Upload a file into *container_path* as a new File or Image object.

        :param container_path: Path of the Plone folder that will contain
            the new object.
        :type container_path: str
        :param filename: Desired filename (also used as default title).
        :type filename: str
        :param source: The file data — accepts a path string, :class:`pathlib.Path`,
            ``bytes``, or a binary file-like object.
        :type source: IO[bytes] or bytes or pathlib.Path or str
        :param field: The schema field name to target (``"file"`` or ``"image"``).
        :type field: str
        :param content_type: MIME type.  Auto-detected from *filename* when not given.
        :type content_type: str or None
        :param title: Object title.  Defaults to *filename*.
        :type title: str
        :param extra_fields: Any additional fields to PATCH onto the created object.
        """
        _name, fobj, detected_mime = _open_file(source)
        mime = content_type or detected_mime
        portal_type = "Image" if mime.startswith("image/") else "File"

        payload: dict[str, Any] = {
            "@type": portal_type,
            "title": title or filename,
            field: {
                "filename": filename,
                "content-type": mime,
                "encoding": "base64",
                "data": _encode_b64(fobj.read()),
            },
            **extra_fields,
        }
        return self._post(container_path, json=payload)

    def update_file_field(
        self,
        path: str,
        source: _FileLike,
        *,
        field: str = "file",
        filename: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Replace the file data on an existing content object's *field*.

        :param path: Path to the existing content object.
        :type path: str
        :param source: New file data.
        :type source: IO[bytes] or bytes or pathlib.Path or str
        :param field: Schema field to update (``"file"``, ``"image"``, etc.)
        :type field: str
        :param filename: Override filename (auto-detected from *source* when omitted).
        :type filename: str or None
        :param content_type: Override MIME type.
        :type content_type: str or None
        """
        _name, fobj, detected_mime = _open_file(source)
        payload = {
            field: {
                "filename": filename or _name,
                "content-type": content_type or detected_mime,
                "encoding": "base64",
                "data": _encode_b64(fobj.read()),
            }
        }
        return self._patch(path, json=payload)

    # ------------------------------------------------------------------
    # TUS (chunked upload — Plone 6+)
    # ------------------------------------------------------------------

    def tus_upload(
        self,
        container_path: str,
        source: _FileLike,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> dict[str, Any]:
        """
        Upload a file using the TUS resumable upload protocol.

        Plone 6 exposes ``@tus-upload`` on containers.  This method
        handles the full handshake: ``POST`` to create the upload slot,
        then ``PATCH`` chunks until complete.

        :param container_path: Destination folder path.
        :type container_path: str
        :param source: File data.
        :type source: IO[bytes] or bytes or pathlib.Path or str
        :param filename: Filename hint sent to the server.
        :type filename: str or None
        :param content_type: MIME type hint.
        :type content_type: str or None
        :param chunk_size: Bytes per chunk (default 1 MiB).
        :type chunk_size: int
        """
        _name, fobj, detected_mime = _open_file(source)
        fname = filename or _name
        mime = content_type or detected_mime

        # Read all data (for now — streaming TUS would need a different approach)
        data = fobj.read()
        total = len(data)

        # Step 1: initiate upload
        init_resp = self._conn.post(
            f"{container_path}/@tus-upload",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": str(total),
                "Upload-Metadata": (
                    f"filename {_b64_str(fname)},content-type {_b64_str(mime)}"
                ),
            },
        )
        upload_url = init_resp.headers.get("Location", "")
        if not upload_url:
            raise ValueError("TUS server did not return a Location header")

        # Step 2: send chunks
        offset = 0
        while offset < total:
            chunk = data[offset : offset + chunk_size]
            patch_resp = self._conn._session.patch(
                upload_url,
                data=chunk,
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Offset": str(offset),
                    "Content-Type": "application/offset+octet-stream",
                    "Content-Length": str(len(chunk)),
                },
                timeout=self._conn._config.timeout,
            )
            if patch_resp.status_code not in (200, 204):
                from ..exceptions import PloneAPIError

                raise PloneAPIError(
                    f"TUS PATCH failed: {patch_resp.status_code}",
                    status_code=patch_resp.status_code,
                )
            offset += len(chunk)

        # The server returns the new object representation after the last chunk
        return patch_resp.json() if patch_resp.content else {}

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download(self, path: str, field: str = "file") -> bytes:
        """
        Download the raw bytes of a file field.

        :param path: Content object path.
        :type path: str
        :param field: Field name (``"file"``, ``"image"``, …).
        :type field: str
        """
        response = self._conn.get(f"{path}/@download/{field}")
        return response.content

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def image_scales(self, path: str) -> dict[str, Any]:
        """Return all available image scales for *path*."""
        return self._get(f"{path}/@images")

    def image_scale(self, path: str, field: str, scale: str) -> dict[str, Any]:
        """
        Return metadata (URL, width, height) for a specific image scale.

        :param path: Content object path.
        :type path: str
        :param field: Image field name, typically ``"image"``.
        :type field: str
        :param scale: Scale name, e.g. ``"preview"``, ``"thumb"``, ``"mini"``.
        :type scale: str
        """
        return self._get(f"{path}/@images/{field}/{scale}")

    def download_scale(self, path: str, field: str, scale: str) -> bytes:
        """Download the raw bytes of an image scale."""
        response = self._conn.get(f"{path}/@images/{field}/{scale}")
        return response.content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode()


def _b64_str(value: str) -> str:
    import base64

    return base64.b64encode(value.encode()).decode()
