"""One example of the services reference, as the page definitions write it."""

from dataclasses import dataclass


@dataclass
class Example:
    """A call to one manager method, run against a real site.

    :param method: ``manager.method``, such as ``content.get``.
    :param code: Python shown on the page. ``client`` is the client, and the
        value of a last line that is an expression is the answer. Names stay
        defined for the next examples of the page.
    :param cli: Command shown on the page, run after ``undo``.
    :param setup: Python run first, and not shown.
    :param undo: Python run after ``code`` and after ``cli``, and not shown, so
        that both start from the same state.
    :param title: Heading of a second example of the same method.
    :param keep: Keys to keep of a dictionary, or of each entry of a list.
    :param item_keep: Keys to keep of each entry in the lists of a dictionary.
    :param limit: Entries to keep of those lists.
    :param doc: Page of the ``plone.restapi`` documentation, without extension.
    :param text: A sentence to add below the docstring's summary.
    """

    method: str
    code: str
    cli: str = ""
    setup: str = ""
    undo: str = ""
    title: str = ""
    keep: tuple[str, ...] = ()
    item_keep: tuple[str, ...] = ()
    limit: int = 0
    doc: str = ""
    text: str = ""
