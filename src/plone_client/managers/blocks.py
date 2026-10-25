"""
Blocks & slots manager — Volto-specific endpoints.

Covers:
- ``@blocks``        — block type registry
- ``@slots``         — persistent slots (site/section/content level)
- ``@blocksfield``   — serialisation helper for blocks fields
- ``@available-blocks`` — available block types at a given context
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class BlocksManager(BaseManager):
    """
    Interact with Volto blocks and slots via plone.restapi.

    Slots are Volto's mechanism for injecting persistent content blocks
    at a path (and all descendants) without editing each page.
    """

    # ------------------------------------------------------------------
    # Block type registry
    # ------------------------------------------------------------------

    def available_block_types(self, path: str = "/") -> dict[str, Any]:
        """Return block types available at *path*."""
        return self._get(f"{path}/@available-blocks")

    # ------------------------------------------------------------------
    # Slots — site / section / content
    # ------------------------------------------------------------------

    def get_slots(self, path: str) -> dict[str, Any]:
        """
        Get all slots defined at *path* (and inherited from ancestors).

        The response includes slots grouped by their anchor
        (e.g. ``"above-content"``, ``"below-content"``).
        """
        return self._get(f"{path}/@slots")

    def get_slot(self, path: str, slot_name: str) -> dict[str, Any]:
        """Get a specific slot by name at *path*."""
        return self._get(f"{path}/@slots/{slot_name}")

    def create_slot(
        self,
        path: str,
        slot_name: str,
        blocks: dict[str, Any],
        blocks_layout: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a slot at *path*.

        :param path: Context path.  Use ``"/"`` for a site-wide slot.
        :type path: str
        :param slot_name: Slot anchor name, e.g. ``"above-content"``.
        :type slot_name: str
        :param blocks: Dict of block id → block data.
        :type blocks: dict
        :param blocks_layout: Ordering dict ``{"items": ["block-uid-1", ...]}``.
            Auto-generated as a single-item list when not provided.
        :type blocks_layout: dict or None
        """
        payload: dict[str, Any] = {"blocks": blocks}
        if blocks_layout is not None:
            payload["blocks_layout"] = blocks_layout
        else:
            payload["blocks_layout"] = {"items": list(blocks.keys())}
        return self._post(f"{path}/@slots/{slot_name}", json=payload)

    def update_slot(
        self,
        path: str,
        slot_name: str,
        blocks: dict[str, Any],
        blocks_layout: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an existing slot."""
        payload: dict[str, Any] = {"blocks": blocks}
        if blocks_layout is not None:
            payload["blocks_layout"] = blocks_layout
        return self._patch(f"{path}/@slots/{slot_name}", json=payload)

    def delete_slot(self, path: str, slot_name: str) -> None:
        """Delete a slot from *path*."""
        self._delete(f"{path}/@slots/{slot_name}")

    # ------------------------------------------------------------------
    # Blocks field serialisation
    # ------------------------------------------------------------------

    def deserialize_blocks(self, path: str, blocks: dict[str, Any]) -> dict[str, Any]:
        """
        Run the server-side block deserialiser for *blocks* in the context of *path*.

        Useful when you need to translate Volto block data (e.g. internal
        UIDs) before saving.
        """
        return self._post(f"{path}/@blocksfield", json={"blocks": blocks})
