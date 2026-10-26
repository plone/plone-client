"""Site configuration and maintenance."""

from .base import BaseManager
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any


class RegistryManager(BaseManager):
    """Configuration registry (``@registry``)."""

    def get(self, key: str) -> Any:
        """Value of a registry record.

        :param key: Record name, such as ``plone.site_title``.
        :returns: The value.
        """
        return self._client.get(f"/@registry/{key}")

    def list(self, query: str | None = None) -> Iterator[dict[str, Any]]:
        """Registry records.

        :param query: Only records whose name contains this text.
        :returns: Each record, with ``name``, ``value`` and ``schema``.
        """
        return self._client.iter_items("/@registry", {"q": query, "b_size": 100})

    def update(self, values: Mapping[str, Any]) -> None:
        """Change registry records.

        :param values: New values by record name.
        """
        self._client.patch("/@registry", dict(values))

    def set(self, key: str, value: Any) -> None:
        """Change one registry record.

        :param key: Record name.
        :param value: New value.
        """
        self.update({key: value})


class ControlpanelsManager(BaseManager):
    """Control panels (``@controlpanels``)."""

    def list(self) -> list[dict[str, Any]]:
        """Control panels of the site.

        :returns: ``@id``, ``title`` and ``group`` of each panel.
        """
        return self._client.get("/@controlpanels")

    def get(self, panel: str, item: str | None = None) -> dict[str, Any]:
        """A control panel, or an item inside it.

        :param panel: Panel id, such as ``editing`` or ``dexterity-types``.
        :param item: Item id, such as a content type in ``dexterity-types``.
        :returns: Its schema and data.
        """
        path = f"/@controlpanels/{panel}/{item}" if item else f"/@controlpanels/{panel}"
        return self._client.get(path)

    def update(
        self, panel: str, data: Mapping[str, Any], *, item: str | None = None
    ) -> None:
        """Change settings of a control panel, or of an item inside it.

        :param panel: Panel id.
        :param data: New values.
        :param item: Item id.
        """
        path = f"/@controlpanels/{panel}/{item}" if item else f"/@controlpanels/{panel}"
        self._client.patch(path, dict(data))

    def create(self, panel: str, data: Mapping[str, Any]) -> dict[str, Any]:
        """Add an item to a control panel, such as a content type.

        :param panel: Panel id, such as ``dexterity-types``.
        :param data: Data of the new item.
        :returns: The new item.
        """
        return self._client.post(f"/@controlpanels/{panel}", dict(data))

    def delete(self, panel: str, item: str) -> None:
        """Remove an item from a control panel.

        :param panel: Panel id.
        :param item: Item id.
        """
        self._client.delete(f"/@controlpanels/{panel}/{item}")


class AddonsManager(BaseManager):
    """Add-ons (``@addons``)."""

    def list(self) -> dict[str, Any]:
        """Add-ons available on the site.

        :returns: ``items``, each with ``is_installed`` and ``upgrade_info``.
        """
        return self._client.get("/@addons")

    def get(self, addon: str) -> dict[str, Any]:
        """One add-on.

        :param addon: Add-on id, such as ``plone.app.multilingual``.
        :returns: The add-on.
        """
        return self._client.get(f"/@addons/{addon}")

    def install(self, addon: str) -> dict[str, Any]:
        """Install an add-on.

        :param addon: Add-on id.
        :returns: The add-ons, after the change.
        """
        return self._client.post(f"/@addons/{addon}/install")

    def uninstall(self, addon: str) -> dict[str, Any]:
        """Uninstall an add-on.

        :param addon: Add-on id.
        :returns: The add-ons, after the change.
        """
        return self._client.post(f"/@addons/{addon}/uninstall")

    def upgrade(self, addon: str) -> dict[str, Any]:
        """Run the pending upgrade steps of an add-on.

        :param addon: Add-on id.
        :returns: The add-ons, after the change.
        """
        return self._client.post(f"/@addons/{addon}/upgrade")

    def install_profile(self, addon: str, profile: str) -> dict[str, Any]:
        """Import a GenericSetup profile of an add-on.

        :param addon: Add-on id.
        :param profile: Profile name, such as ``default``.
        :returns: The add-ons, after the change.
        """
        return self._client.post(f"/@addons/{addon}/import/{profile}")


class ContentRulesManager(BaseManager):
    """Content rules assigned to a folder (``@content-rules``)."""

    def get(self, ref: str = "/") -> dict[str, Any]:
        """Rules assigned to a folder, and rules that could be.

        :param ref: Path or URL of the folder.
        :returns: ``content-rules`` with ``assigned_rules`` and
            ``addable_rules``.
        """
        return self._client.get(self._service(ref, "@content-rules"))

    def assign(self, ref: str, rule_id: str) -> None:
        """Assign a rule to a folder.

        :param ref: Path or URL of the folder.
        :param rule_id: Rule id.
        """
        self._client.post(self._service(ref, f"@content-rules/{rule_id}"))

    def unassign(self, ref: str, rule_ids: str | Iterable[str]) -> None:
        """Remove rules from a folder.

        :param ref: Path or URL of the folder.
        :param rule_ids: Rule id, or several.
        """
        ids = [rule_ids] if isinstance(rule_ids, str) else list(rule_ids)
        self._client.delete(self._service(ref, "@content-rules"), {"rule_ids": ids})

    def _buttons(self, ref: str, button: str, rule_ids: str | Iterable[str]) -> None:
        """Press a button of the rules form for some rules.

        :param ref: Path or URL of the folder.
        :param button: ``Enable``, ``Disable``, ``Bubble`` or ``NoBubble``.
        :param rule_ids: Rule id, or several.
        """
        ids = [rule_ids] if isinstance(rule_ids, str) else list(rule_ids)
        self._client.patch(
            self._service(ref, "@content-rules"),
            {f"form.button.{button}": True, "rule_ids": ids},
        )

    def enable(self, ref: str, rule_ids: str | Iterable[str]) -> None:
        """Enable rules on a folder.

        :param ref: Path or URL of the folder.
        :param rule_ids: Rule id, or several.
        """
        self._buttons(ref, "Enable", rule_ids)

    def disable(self, ref: str, rule_ids: str | Iterable[str]) -> None:
        """Disable rules on a folder.

        :param ref: Path or URL of the folder.
        :param rule_ids: Rule id, or several.
        """
        self._buttons(ref, "Disable", rule_ids)

    def apply_to_subfolders(
        self, ref: str, rule_ids: str | Iterable[str], *, apply: bool = True
    ) -> None:
        """Apply rules to the subfolders of a folder, or stop doing so.

        :param ref: Path or URL of the folder.
        :param rule_ids: Rule id, or several.
        :param apply: ``False`` stops applying them to subfolders.
        """
        self._buttons(ref, "Bubble" if apply else "NoBubble", rule_ids)

    def move(self, ref: str, rule_id: str, *, up: bool = True) -> None:
        """Move a rule up or down in the folder's list.

        :param ref: Path or URL of the folder.
        :param rule_id: Rule id.
        :param up: ``False`` moves it down.
        """
        self._client.patch(
            self._service(ref, "@content-rules"),
            {"operation": "move_up" if up else "move_down", "rule_id": rule_id},
        )


class SystemManager(BaseManager):
    """Information about the site and maintenance tasks."""

    def site(self) -> dict[str, Any]:
        """Site settings used by frontends (``@site``).

        :returns: Title, logo, languages and similar settings.
        """
        return self._client.get("/@site")

    def system(self) -> dict[str, Any]:
        """Versions of Plone, Python, Zope and other components (``@system``).

        Needs the *Manage portal* permission.

        :returns: Version numbers and upgrade state.
        """
        return self._client.get("/@system")

    def database(self) -> dict[str, Any]:
        """Database statistics (``@database``).

        :returns: Size, object count, cache and connection details.
        """
        return self._client.get("/@database")

    def transactions(self) -> list[dict[str, Any]]:
        """Recent transactions (``@transactions``).

        :returns: ``id``, ``time``, ``username`` and ``description`` of each.
        """
        return self._client.get("/@transactions")

    def revert_transactions(
        self, transaction_ids: str | Iterable[str]
    ) -> dict[str, Any]:
        """Undo transactions.

        :param transaction_ids: Id of a transaction, or several.
        :returns: A confirmation message.
        """
        ids = (
            [transaction_ids]
            if isinstance(transaction_ids, str)
            else list(transaction_ids)
        )
        return self._client.patch("/@transactions", {"transaction_ids": ids})

    def upgrade_info(self) -> dict[str, Any]:
        """Pending upgrade steps of the site (``@upgrade``).

        :returns: Versions and the upgrade steps to run.
        """
        return self._client.get("/@upgrade")

    def upgrade(self, *, dry_run: bool = True) -> dict[str, Any]:
        """Run the site's upgrade steps.

        :param dry_run: Only report what would run.
        :returns: The upgrade report.
        """
        return self._client.post("/@upgrade", {"dry_run": dry_run})

    def login_providers(self) -> dict[str, Any]:
        """External authentication providers (``GET @login``).

        :returns: ``options`` with each provider's ``url``.
        """
        return self._client.get("/@login")

    def email_send(
        self,
        to: str,
        sender: str,
        message: str,
        *,
        subject: str | None = None,
        name: str | None = None,
    ) -> None:
        """Send an email through the site (``@email-send``).

        :param to: Recipient address.
        :param sender: Sender address.
        :param message: Body of the message.
        :param subject: Subject.
        :param name: Sender name.
        """
        data = {"to": to, "from": sender, "message": message}
        data.update({k: v for k, v in (("subject", subject), ("name", name)) if v})
        self._client.post("/@email-send", data)

    def email_notification(
        self,
        sender: str,
        message: str,
        *,
        subject: str | None = None,
        name: str | None = None,
    ) -> None:
        """Send a message to the site owner, like the contact form does.

        :param sender: Sender address.
        :param message: Body of the message.
        :param subject: Subject.
        :param name: Sender name.
        """
        data = {"from": sender, "message": message}
        data.update({k: v for k, v in (("subject", subject), ("name", name)) if v})
        self._client.post("/@email-notification", data)
