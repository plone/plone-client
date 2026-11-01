"""Generate the services reference by running every example on a real site.

``plone.restapi`` writes the requests and answers of its documentation from its
tests, so they cannot drift from the code. This does the same for plone-client.
Each page of ``docs/_generate/services/`` lists examples; each one runs here,
its requests are recorded, and the page in ``docs/_generated/services/`` shows
them with what the site answered.

The script starts a fresh site with Docker Compose, unless
``SERVICES_SITE_RUNNING`` is set, and removes it at the end. ``--check`` writes
nothing, and fails when an answer differs from the page in the tree, or when a
public method of a manager has no example.
"""

from pathlib import Path
from plone_client import PloneClient
from plone_client.managers.base import BaseManager
from service_example import Example
from typing import Any

import ast
import contextlib
import difflib
import httpx
import importlib.util
import inspect
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile


ROOT = Path(__file__).parents[2]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / "docs" / "_checks"))

from run import normalize


GENERATED = ROOT / "docs" / "_generated" / "services"
ENDPOINTS = ROOT.parent / "plone.restapi" / "docs" / "source" / "endpoints"
ENDPOINTS_URL = "https://6.docs.plone.org/plone.restapi/docs/source/endpoints"
PLONE_PORT = os.environ.get("PLONE_PORT", "8480")
VOLTO_PORT = os.environ.get("VOLTO_PORT", "3400")
PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "pc-services")
SITE = f"http://localhost:{PLONE_PORT}/Plone"
FRONTEND = f"http://localhost:{VOLTO_PORT}"
CREDENTIALS = {"username": "admin", "password": "admin"}
#: Run order. Translations change the site, so their page goes last.
PAGES = [
    "content",
    "search",
    "workflow",
    "files",
    "navigation",
    "people",
    "types",
    "site",
    "related-content",
]
HIDDEN_HEADERS = {
    "accept-encoding",
    "connection",
    "content-length",
    "cookie",
    "host",
    "user-agent",
}
#: What changes from one run to the next, besides what ``normalize`` handles.
VOLATILE = [
    (re.compile(r'("token": )"[^"]+"'), r'\1"<TOKEN>"'),
    (re.compile(r'("comment_id": )"[^"]+"'), r'\1"<ID>"'),
    (re.compile(r"@comments/\d+"), "@comments/<ID>"),
    (re.compile(r'("id": )"[A-Za-z0-9+/=]{10,}"'), r'\1"<ID>"'),
    (re.compile(r'("transaction_ids": \[\s*)"[^"]+"'), r'\1"<ID>"'),
    (re.compile(r"transaction_ids.{0,6}\[.{0,4}[A-Za-z0-9+/=]+"), "<IDS>"),
    (re.compile(r"Authorization: Bearer \S+"), "Authorization: Bearer <TOKEN>"),
    (re.compile(r"Lock-Token: \S+"), "Lock-Token: <TOKEN>"),
    (re.compile(r"Upload-Metadata: .*"), "Upload-Metadata: <METADATA>"),
    (re.compile(r"@tus-upload/\w+"), "@tus-upload/<ID>"),
    (re.compile(r"@tus-replace/\w+"), "@tus-replace/<ID>"),
    (re.compile(r'("\w+_version": )"[^"]+"'), r'\1"<VERSION>"'),
    (re.compile(r"of \d+ entries"), "of <NUMBER> entries"),
    (re.compile(r"\bPlone_[\d_]+"), "Plone_<NUMBER>_"),
    (re.compile(r"\b\d{6,}\b"), "<NUMBER>"),
]


def to_page(text: str) -> str:
    """Write a text with the ports that the pages show.

    :param text: Anything that came from the site.
    :returns: The text with the documented ports.
    """
    return text.replace(f":{PLONE_PORT}", ":8080").replace(f":{VOLTO_PORT}", ":3000")


def comparable(text: str) -> str:
    """Remove what changes from one run to the next.

    :param text: A generated page.
    :returns: The normalized text.
    """
    text = normalize(text)
    for pattern, replacement in VOLATILE:
        text = pattern.sub(replacement, text)
    return text


def compose(*arguments: str) -> str:
    """Run ``docker compose`` on the site of this script.

    :param arguments: Its arguments.
    :returns: What it printed.
    """
    env = {
        **os.environ,
        "SEED_SCRIPT": "/repository/docs/_checks/seed.py",
        "PLONE_PORT": PLONE_PORT,
        "VOLTO_PORT": VOLTO_PORT,
    }
    command = ["docker", "compose", "-p", PROJECT, *arguments]
    done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if done.returncode:
        print(done.stderr, file=sys.stderr)
    done.check_returncode()
    return done.stdout


def wait_for_seed() -> None:
    """Wait for the sample content, which ``up --wait`` does not wait for.

    :raises SystemExit: If the seed failed.
    """
    container = compose("ps", "--all", "--quiet", "seed").strip()
    done = subprocess.run(
        ["docker", "wait", container], check=True, capture_output=True, text=True
    )
    if done.stdout.strip() != "0":
        print(compose("logs", "seed"), file=sys.stderr)
        raise SystemExit(f"The seed failed with exit code {done.stdout.strip()}")


def load_page(name: str) -> Any:
    """Import the definitions of a page.

    :param name: Name of the page.
    :returns: Its module, with ``EXAMPLES`` and ``NOT_RUN``.
    """
    path = HERE / "services" / f"{name.replace('-', '_')}.py"
    spec = importlib.util.spec_from_file_location(f"page_{path.stem}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def managers() -> dict[str, type[BaseManager]]:
    """The managers of a client.

    :returns: Classes by attribute name.
    """
    with PloneClient(SITE) as client:
        return {
            name: type(value)
            for name, value in vars(client).items()
            if isinstance(value, BaseManager)
        }


def public_methods() -> dict[str, Any]:
    """Every public method of every manager.

    :returns: Functions by ``manager.method``.
    """
    found: dict[str, Any] = {}
    for name, manager in managers().items():
        for attribute, value in vars(manager).items():
            if not attribute.startswith("_") and inspect.isfunction(value):
                found[f"{name}.{attribute}"] = value
    return found


def summary(function: Any) -> str:
    """The first sentence of a docstring, in Markdown.

    :param function: A function or class.
    :returns: One line.
    """
    text = (inspect.getdoc(function) or "").split("\n\n")[0]
    return " ".join(text.split()).replace("``", "`")


def run_code(code: str, names: dict[str, Any]) -> Any:
    """Run a snippet.

    :param code: The Python.
    :param names: Its global names, which stay for the next one.
    :returns: The value of a last line that is an expression, or ``None``.
    """
    tree = ast.parse(code)
    last = tree.body[-1] if tree.body else None
    if isinstance(last, ast.Expr):
        tree.body.pop()
        exec(compile(tree, "<example>", "exec"), names)
        expression = ast.Expression(last.value)
        return eval(compile(expression, "<example>", "eval"), names)
    exec(compile(tree, "<example>", "exec"), names)
    return None


def run_command(command: str, workdir: Path) -> str:
    """Run a command of the page.

    :param command: The shell command.
    :param workdir: Directory of the run.
    :returns: What it printed.
    :raises SystemExit: If it fails.
    """
    env = {
        **os.environ,
        "HOME": str(workdir),
        "PATH": f"{ROOT / '.venv/bin'}:{os.environ['PATH']}",
        "PLONE_CLIENT_CONFIG": str(workdir / "config.toml"),
        "PLONE_CLIENT_URL": SITE,
        "PLONE_CLIENT_USERNAME": "admin",
        "PLONE_CLIENT_PASSWORD": "admin",
        "PLONE_CLIENT_FRONTEND_URL": FRONTEND,
    }
    done = subprocess.run(
        ["bash", "-c", command],
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        timeout=120,
    )
    if done.returncode:
        raise SystemExit(f"{command}: exit {done.returncode}\n{done.stdout}")
    return done.stdout


def body_text(request: httpx.Request) -> str:
    """The body of a request, for the page.

    :param request: The request.
    :returns: Indented JSON, the text, or an empty string.
    """
    if not request.content:
        return ""
    try:
        return json.dumps(json.loads(request.content), indent=2, ensure_ascii=False)
    except ValueError:
        return request.content.decode("utf-8", "replace")


def http_text(request: httpx.Request) -> str:
    """A request as a block in the ``http`` lexer.

    :param request: The request.
    :returns: The block.
    """
    target = request.url.raw_path.decode()
    lines = [
        f"{request.method} {target} HTTP/1.1",
        f"Host: {request.url.netloc.decode()}",
    ]
    for key, value in request.headers.items():
        if key.lower() in HIDDEN_HEADERS:
            continue
        if value.startswith("Bearer "):
            value = "Bearer TOKEN"
        lines.append(f"{'-'.join(p.capitalize() for p in key.split('-'))}: {value}")
    body = body_text(request)
    return "\n".join(lines) + (f"\n\n{body}" if body else "")


def curl_text(request: httpx.Request) -> str:
    """The same request as a ``curl`` command.

    :param request: The request.
    :returns: The command, or an empty string for a token or a binary body.
    """
    if request.headers.get("authorization", "").startswith("Bearer"):
        return ""
    parts = ["curl", "-i", "-X", request.method, shlex.quote(str(request.url))]
    for key, value in request.headers.items():
        if key.lower() in {*HIDDEN_HEADERS, "authorization"}:
            continue
        parts += ["-H", shlex.quote(f"{key}: {value}")]
    if "authorization" in request.headers:
        parts += ["-u", "admin:admin"]
    if request.content:
        parts += ["--data-raw", shlex.quote(request.content.decode("utf-8", "replace"))]
    return " ".join(parts)


def trim(value: Any, example: Example) -> tuple[Any, list[str]]:
    """Keep the part of an answer that the example selects.

    :param value: The answer.
    :param example: The example.
    :returns: The shorter answer, and sentences that say what was left out.
    """
    notes: list[str] = []

    def keys(names: tuple[str, ...]) -> str:
        return ", ".join(f"`{name}`" for name in names)

    def require(entry: dict[str, Any], names: tuple[str, ...]) -> None:
        missing = [name for name in names if name not in entry]
        if missing:
            raise SystemExit(f"{example.method}: no key {missing} in {list(entry)}")

    def entries(items: list[Any], names: tuple[str, ...]) -> list[Any]:
        for entry in items:
            if names and isinstance(entry, dict):
                require(entry, names)
        if example.limit and len(items) > example.limit:
            notes.append(f"This shows {example.limit} of {len(items)} entries.")
            items = items[: example.limit]
        if names:
            return [
                {k: v for k, v in entry.items() if k in names}
                if isinstance(entry, dict)
                else entry
                for entry in items
            ]
        return items

    if isinstance(value, list):
        if example.keep:
            notes.append(f"This shows only {keys(example.keep)} of each entry.")
        return entries(value, example.keep), notes
    if not isinstance(value, dict):
        return value, notes
    if example.keep:
        require(value, example.keep)
        notes.append(f"This shows only {keys(example.keep)}.")
        value = {k: v for k, v in value.items() if k in example.keep}
    if example.item_keep or example.limit:
        if example.item_keep:
            names = keys(example.item_keep)
            notes.append(f"This shows only {names} of each entry.")
        value = {
            k: entries(v, example.item_keep) if isinstance(v, list) else v
            for k, v in value.items()
        }
    return value, notes


def answer_block(value: Any, status: int | None) -> list[str]:
    """Markdown for what a method returned.

    :param value: The value, already trimmed.
    :param status: Status of the last response.
    :returns: Lines of Markdown.
    """
    if value is None:
        return [f"The site answers `{status}`, and the method returns `None`.", ""]
    if isinstance(value, bytes):
        return [f"The method returns the {len(value)} bytes of the file.", ""]
    text = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    return ["```json", to_page(text), "```", ""]


def tabs(example: Example, cli_output: str, requests: list[httpx.Request]) -> list[str]:
    """The tabs of an example.

    :param example: The example.
    :param cli_output: What the command printed.
    :param requests: The requests of the Python code.
    :returns: Lines of Markdown.
    """

    def tab(label: str, key: str, body: list[str]) -> list[str]:
        return [f"````{{tab-item}} {label}", f":sync: {key}", "", *body, "````", ""]

    out = ["`````{tab-set}", ":sync-group: service-example", ""]
    out += tab("Python", "python", ["```python", example.code.strip(), "```"])
    if example.cli:
        body = ["```shell", example.cli, "```"]
        if cli_output.strip():
            language = "json" if cli_output.lstrip()[:1] in "[{" else "text"
            body += ["", f"```{language}", to_page(cli_output.strip()), "```"]
        out += tab("Command line", "cli", body)
    http: list[str] = []
    curl: list[str] = []
    for request in requests:
        http += ["```http", to_page(http_text(request)), "```", ""]
        command = curl_text(request)
        if command:
            curl.append(to_page(command))
    if curl:
        http += ["```shell", *curl, "```", ""]
    out += tab("HTTP", "http", http[:-1])
    out[-1:] = ["`````", ""]
    return out


class Runner:
    """Run the examples of the pages, with one client per run.

    :param client: The client that runs the examples.
    :param workdir: Directory of the commands and of local files.
    """

    def __init__(self, client: PloneClient, workdir: Path) -> None:
        self.client = client
        self.workdir = workdir
        self.requests: list[httpx.Request] = []
        self.responses: list[httpx.Response] = []
        self.record(client)

    def record(self, client: PloneClient) -> None:
        """Record the requests of a client.

        :param client: The client; examples may log in as another user.
        """
        client._http.event_hooks["request"].append(self.requests.append)
        client._http.event_hooks["response"].append(self.responses.append)

    def dry(self, example: Example, names: dict[str, Any]) -> list[httpx.Request]:
        """The requests an example would send, without sending them.

        :param example: The example.
        :param names: Names of the page.
        :returns: The requests.
        """
        sent: list[httpx.Request] = []

        def answer(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            return httpx.Response(200, json={})

        site = PloneClient(
            SITE,
            dry_run=True,
            frontend_url=FRONTEND,
            transport=httpx.MockTransport(answer),
            **CREDENTIALS,
        )
        with site:
            run_code(example.code, {**names, "client": site})
            skipped = [
                site._http.build_request(
                    entry["method"],
                    entry["url"],
                    params=entry.get("params"),
                    json=entry.get("json"),
                    headers={"Authorization": "Basic YWRtaW46YWRtaW4="},
                )
                for entry in site.dry_run_log
            ]
        return sent + skipped

    def section(
        self, example: Example, names: dict[str, Any], reason: str | None
    ) -> list[str]:
        """Run an example, and write its section.

        :param example: The example.
        :param names: Names of the page.
        :param reason: Why it does not run against a site, if so.
        :returns: Lines of Markdown.
        """
        print(f"  {example.method}", flush=True)
        if example.setup:
            run_code(example.setup, names)
        self.requests.clear()
        self.responses.clear()
        out: list[str] = []
        if reason:
            requests = self.dry(example, names)
            out += [
                "```{note}",
                f"This example was not run against a site, because {reason}",
                "The request below was built, and not sent.",
                "```",
                "",
                *tabs(example, "", requests),
            ]
            return self.links(example, requests, False) + out
        try:
            value = run_code(example.code, names)
        except Exception as error:
            raise SystemExit(f"{example.method}: {error!r}") from error
        requests = list(self.requests)
        status = self.responses[-1].status_code if self.responses else None
        if example.undo:
            run_code(example.undo, names)
        cli_output = ""
        if example.cli:
            cli_output = run_command(example.cli, self.workdir)
            if example.undo:
                run_code(example.undo, names)
        trimmed, notes = trim(value, example)
        out += tabs(example, cli_output, requests)
        out += answer_block(trimmed, status)
        if notes:
            out += [" ".join(dict.fromkeys(notes)), ""]
        return self.links(example, requests, True) + out

    def links(
        self, example: Example, requests: list[httpx.Request], ran: bool
    ) -> list[str]:
        """The line that names the service.

        :param example: The example.
        :param requests: Its requests.
        :param ran: Whether it ran.
        :returns: Lines of Markdown.
        """
        calls: list[str] = []
        for request in requests:
            path = request.url.path.removeprefix("/Plone").removeprefix("/++api++")
            call = f"`{request.method} {path or '/'}`"
            if call not in calls:
                calls.append(call)
        line = ", ".join(calls) if calls else "No request"
        if example.doc:
            if ENDPOINTS.exists() and not (ENDPOINTS / f"{example.doc}.md").exists():
                raise SystemExit(f"{example.method}: no endpoint page {example.doc}")
            url = f"{ENDPOINTS_URL}/{example.doc}.html"
            line += f" ([`plone.restapi` documentation]({url}))"
        return [f"Calls {line}.", ""]


def write_page(name: str, runner: Runner, seen: dict[str, int]) -> str:
    """Run a page.

    :param name: Name of the page.
    :param runner: The runner.
    :param seen: Counts the examples of each method.
    :returns: The Markdown of the page.
    """
    print(name, flush=True)
    page = load_page(name)
    methods = public_methods()
    classes = managers()
    names: dict[str, Any] = {"client": runner.client, "record": runner.record}
    out = [
        "<!-- Generated by docs/_generate/services.py: do not edit. -->",
        "<!-- vale off -->",
        "",
    ]
    current_manager = ""
    current_method = ""
    for example in page.EXAMPLES:
        if example.method not in methods:
            raise SystemExit(f"{example.method} is not a method of a manager")
        manager, method = example.method.split(".")
        cls = classes[manager]
        if manager != current_manager:
            current_manager = manager
            reference = f"~{cls.__module__}.{cls.__name__}"
            out += [f"## `client.{manager}`", "", f"{{class}}`{reference}`.", ""]
            out += [summary(cls), ""]
        if example.method != current_method:
            current_method = example.method
            out += [f"### `client.{example.method}`", ""]
            out += [summary(methods[example.method]), ""]
            out += [f"See {{meth}}`~{cls.__module__}.{cls.__name__}.{method}`.", ""]
        if example.title:
            out += [f"#### {example.title}", ""]
        if example.text:
            out += [example.text, ""]
        out += runner.section(example, names, page.NOT_RUN.get(example.method))
        seen[example.method] = seen.get(example.method, 0) + 1
    return "\n".join(out).rstrip() + "\n"


def report_population(seen: dict[str, int], not_run: dict[str, str]) -> int:
    """Compare the examples with the public methods.

    :param seen: Counts the examples of each method.
    :param not_run: Methods that do not run against a site.
    :returns: The exit code.
    """
    methods = public_methods()
    missing = sorted(set(methods) - set(seen))
    print(
        f"{len(methods)} methods, {sum(seen.values())} examples, {len(not_run)} not run"
    )
    if missing:
        print("No example for: " + ", ".join(missing))
        return 1
    return 0


def main() -> int:
    """Generate the pages, or compare them.

    :returns: The exit code.
    """
    check = "--check" in sys.argv
    selected = [arg for arg in sys.argv[1:] if not arg.startswith("-")] or PAGES
    running = bool(os.environ.get("SERVICES_SITE_RUNNING"))
    seen: dict[str, int] = {}
    not_run: dict[str, str] = {}
    failed = 0
    if not running:
        compose("down", "-v", "--timeout", "2")
        compose("up", "--wait")
        wait_for_seed()
    try:
        with tempfile.TemporaryDirectory(prefix="check-") as directory:
            workdir = Path(directory).resolve()
            os.chdir(workdir)
            client = PloneClient(SITE, frontend_url=FRONTEND, **CREDENTIALS)
            with client, contextlib.ExitStack() as stack:
                stack.callback(os.chdir, ROOT)
                runner = Runner(client, workdir)
                for name in selected:
                    text = write_page(name, runner, seen)
                    not_run.update(load_page(name).NOT_RUN)
                    path = GENERATED / f"{name}.md"
                    if check:
                        old = path.read_text() if path.exists() else ""
                        changes = list(
                            difflib.unified_diff(
                                comparable(old).splitlines(),
                                comparable(text).splitlines(),
                                lineterm="",
                                n=0,
                            )
                        )
                        if changes:
                            print(f"{path.name} is out of date: regenerate it")
                            print("\n".join(changes[:20]))
                            failed = 1
                    else:
                        GENERATED.mkdir(parents=True, exist_ok=True)
                        path.write_text(text)
    finally:
        if not running:
            compose("down", "-v", "--timeout", "2")
    if selected == PAGES:
        failed = report_population(seen, not_run) or failed
    return failed


if __name__ == "__main__":
    sys.exit(main())
