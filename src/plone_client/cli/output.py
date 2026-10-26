"""Output, input parsing and error handling of the command line.

Every command prints JSON on standard output, so its result can be read by
``jq``, by scripts and by agents. Errors go to standard error, also as JSON,
with an exit code that says what kind of error it was (:data:`EXIT_CODES`).
"""

from ..exceptions import PloneAPIError
from ..exceptions import PloneAuthenticationError
from ..exceptions import PloneBadRequestError
from ..exceptions import PloneClientError
from ..exceptions import PloneConfigurationError
from ..exceptions import PloneConflictError
from ..exceptions import PloneConnectionError
from ..exceptions import PloneForbiddenError
from ..exceptions import PloneNotFoundError
from ..exceptions import PloneReadOnlyError
from ..exceptions import PloneServerError
from .state import get_state
from collections.abc import Iterable
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import json
import sys
import typer
import typer.core


#: Exit codes by error class; the first match wins.
EXIT_CODES: tuple[tuple[type[PloneClientError], int], ...] = (
    (PloneConfigurationError, 3),
    (PloneAuthenticationError, 4),
    (PloneForbiddenError, 4),
    (PloneNotFoundError, 5),
    (PloneBadRequestError, 6),
    (PloneConflictError, 6),
    (PloneReadOnlyError, 7),
    (PloneConnectionError, 8),
    (PloneServerError, 9),
)

#: Keys printed for an item when a command does not print it in full.
SUMMARY_FIELDS = ("@id", "@type", "UID", "id", "title", "review_state")


def exit_code(error: PloneClientError) -> int:
    """Exit code for an error.

    :param error: The error.
    :returns: The code from :data:`EXIT_CODES`, or ``1``.
    """
    for error_class, code in EXIT_CODES:
        if isinstance(error, error_class):
            return code
    return 1


def error_payload(error: PloneClientError) -> dict[str, Any]:
    """JSON description of an error.

    :param error: The error.
    :returns: ``{"error": {...}}``.
    """
    if isinstance(error, PloneAPIError):
        details = error.to_dict()
    else:
        details = {"type": error.__class__.__name__, "message": str(error)}
    return {"error": details}


#: Global flags, accepted anywhere on the command line. ``--read-only`` is
#: left out: ``profile add`` has its own.
GLOBAL_FLAGS = frozenset({"-c", "--compact", "-n", "--dry-run", "-v", "--verbose"})
#: Global options that take a value, accepted anywhere on the command line.
#: ``--url`` and ``--username`` are left out: ``profile add`` has its own.
GLOBAL_OPTIONS = frozenset({"-f", "--fields", "-p", "--profile", "--config"})


def hoist_global_options(args: list[str]) -> list[str]:
    """Move the global options in front of the command.

    Click only reads the options of a group before its subcommand, but
    ``plone-client get /news -f title`` is the natural way to write it.

    :param args: Command line arguments.
    :returns: The same arguments, global options first; anything after
        ``--`` is left alone.
    """
    hoisted: list[str] = []
    rest: list[str] = []
    remaining = iter(args)
    for arg in remaining:
        if arg == "--":
            rest.append(arg)
            rest.extend(remaining)
            break
        name = arg.split("=", 1)[0]
        if arg in GLOBAL_FLAGS or (name in GLOBAL_OPTIONS and "=" in arg):
            hoisted.append(arg)
        elif arg in GLOBAL_OPTIONS:
            hoisted.append(arg)
            value = next(remaining, None)
            if value is not None:
                hoisted.append(value)
        else:
            rest.append(arg)
    return hoisted + rest


class PloneGroup(typer.core.TyperGroup):
    """Command group that reports library errors as JSON."""

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        if ctx.parent is None:
            args = hoist_global_options(args)
        return super().parse_args(ctx, args)

    def invoke(self, ctx: Any) -> Any:
        try:
            return super().invoke(ctx)
        except PloneClientError as error:
            text = json.dumps(error_payload(error), indent=2, ensure_ascii=False)
            typer.echo(text, err=True)
            ctx.exit(exit_code(error))
        except ValueError as error:
            payload = {"error": {"type": "ValueError", "message": str(error)}}
            typer.echo(json.dumps(payload, indent=2), err=True)
            ctx.exit(2)


def project(data: Any, fields: Iterable[str]) -> Any:
    """Keep only some keys of the output.

    Applies to a mapping, to each mapping of a list, and to each entry of
    the ``items`` of a batched answer when none of the keys is at its top
    level.

    :param data: Output of a command.
    :param fields: Keys to keep; empty keeps everything.
    :returns: The projected data.
    """
    fields = list(fields)
    if not fields:
        return data
    if isinstance(data, list):
        return [project(entry, fields) for entry in data]
    if isinstance(data, Mapping):
        batched = isinstance(data.get("items"), list)
        if batched and not any(key in data for key in fields):
            return {
                **{key: data[key] for key in ("items_total",) if key in data},
                "items": project(data["items"], fields),
            }
        return {key: data[key] for key in fields if key in data}
    return data


def summary(item: Mapping[str, Any]) -> dict[str, Any]:
    """Short form of an item.

    :param item: A serialized item.
    :returns: Only the keys in :data:`SUMMARY_FIELDS`.
    """
    return {key: item[key] for key in SUMMARY_FIELDS if key in item}


def emit(ctx: typer.Context, data: Any) -> None:
    """Print the output of a command as JSON.

    :param ctx: Typer context.
    :param data: The output.
    """
    state = get_state(ctx)
    data = project(data, state.fields)
    indent = None if state.compact else 2
    typer.echo(json.dumps(data, indent=indent, ensure_ascii=False, default=str))


def parse_value(raw: str) -> Any:
    """Parse a ``--set`` value that is meant to be JSON.

    :param raw: The text after ``:=``.
    :returns: The parsed value.
    :raises ValueError: If it is not valid JSON.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not valid JSON: {raw!r} ({exc.msg})") from None


def parse_assignments(items: Iterable[str]) -> dict[str, Any]:
    """Parse ``--set`` options.

    ``key=value`` sets a string; ``key:=value`` sets a JSON value
    (``subjects:='["a", "b"]'``, ``exclude_from_nav:=true``), as httpie does.

    :param items: The options.
    :returns: Values by key.
    :raises ValueError: If an option has no ``=``.
    """
    data: dict[str, Any] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise ValueError(f"Expected key=value or key:=json, got {item!r}")
        if key.endswith(":"):
            data[key[:-1]] = parse_value(value)
        else:
            data[key] = value
    return data


def read_data(source: str | None) -> dict[str, Any]:
    """Read the ``--data`` option.

    :param source: JSON text, ``@path`` of a JSON file, or ``-`` for
        standard input.
    :returns: The parsed object.
    :raises ValueError: If the data is not a JSON object.
    """
    if not source:
        return {}
    if source == "-":
        text = sys.stdin.read()
    elif source.startswith("@"):
        text = Path(source[1:]).expanduser().read_text()
    else:
        text = source
    data = parse_value(text)
    if not isinstance(data, dict):
        raise ValueError("--data must be a JSON object")
    return data


def payload(
    data: str | None, assignments: Iterable[str], **known: Any
) -> dict[str, Any]:
    """Body of a create or update, from the options of a command.

    :param data: The ``--data`` option.
    :param assignments: The ``--set`` options, applied over ``--data``.
    :param known: Values of dedicated options (``--title``…); ``None`` is ignored.
    :returns: The body.
    """
    body = read_data(data)
    body.update(parse_assignments(assignments))
    body.update({key: value for key, value in known.items() if value is not None})
    return body


def confirm(ctx: typer.Context, message: str, yes: bool) -> None:
    """Ask before a destructive change, unless --yes or --dry-run is given.

    Without a terminal there is nobody to ask, so ``--yes`` is required.

    :param ctx: Typer context.
    :param message: What will happen.
    :param yes: Whether ``--yes`` was given.
    :raises typer.Exit: If the change is not confirmed.
    """
    if yes or get_state(ctx).dry_run:
        return
    if not sys.stdin.isatty():
        typer.echo(f"{message}: pass --yes to confirm", err=True)
        raise typer.Exit(2)
    if not typer.confirm(f"{message}?"):
        raise typer.Exit(1)
