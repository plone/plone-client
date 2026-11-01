# Examples are shown as written, so they may be long.
"""Examples of ``client.files``."""

from service_example import Example


NOT_RUN: dict[str, str] = {}

SETUP = (
    "from pathlib import Path\n"
    'Path("notes.txt").write_text("Meeting notes.\\n")\n'
    'Path("photo.png").write_bytes(client.files.download("/media/logo.png", field="image"))'
)

EXAMPLES = [
    Example(
        "files.upload",
        'client.files.upload("/media", "notes.txt", title="Notes")',
        setup=SETUP,
        cli="plone-client upload /media photo.png --title Photo -f @id,@type,title",
        undo='for path in ("/media/notes.txt", "/media/photo.png"):\n'
        "    if client.exists(path):\n"
        "        client.content.delete(path)",
        keep=("@id", "@type", "title"),
        doc="content-types",
    ),
    Example(
        "files.replace",
        'client.files.replace("/media/readme.txt", b"New text.\\n", filename="readme.txt")',
        doc="content-types",
    ),
    Example(
        "files.download",
        'client.files.download("/media/readme.txt")',
        cli="plone-client download /media/readme.txt -o readme.txt",
    ),
    Example(
        "files.image_scale",
        'client.files.image_scale("/media/logo.png", scale="thumb")',
    ),
    Example(
        "files.tus_upload",
        'client.files.tus_upload("/media", b"A large file.\\n", filename="large.txt")',
        cli="plone-client upload /media notes.txt --tus",
        undo='for path in ("/media/large.txt", "/media/notes.txt"):\n'
        "    if client.exists(path):\n"
        "        client.content.delete(path)",
        doc="tusupload",
    ),
    Example(
        "files.tus_replace",
        'client.files.tus_replace(\n    "/media/readme.txt",\n'
        '    b"Sample file.\\n",\n    filename="readme.txt",\n    field="file",\n)',
        doc="tusupload",
    ),
]
