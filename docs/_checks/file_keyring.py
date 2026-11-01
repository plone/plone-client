"""A keyring in a JSON file, so that checks never touch the real one."""

from keyring.backend import KeyringBackend
from pathlib import Path

import json
import os


class FileKeyring(KeyringBackend):
    """Store secrets in ``$CHECK_KEYRING_FILE``."""

    priority = 1  # type: ignore[assignment]

    @property
    def _path(self) -> Path:
        return Path(os.environ["CHECK_KEYRING_FILE"])

    def _load(self) -> dict[str, str]:
        return json.loads(self._path.read_text()) if self._path.exists() else {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._load().get(f"{service}/{username}")

    def set_password(self, service: str, username: str, password: str) -> None:
        secrets = self._load()
        secrets[f"{service}/{username}"] = password
        self._path.write_text(json.dumps(secrets))

    def delete_password(self, service: str, username: str) -> None:
        secrets = self._load()
        secrets.pop(f"{service}/{username}", None)
        self._path.write_text(json.dumps(secrets))
