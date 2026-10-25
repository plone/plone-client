# Changelog

All notable changes to **plone-client** will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-03-17

### Added

- `PloneClient` — synchronous high-level client with context-manager support.
- `AsyncPloneClient` — async counterpart backed by `httpx` (opt-in via `pip install plone-client[async]`).
- `PloneClientConfig` — dataclass with full environment-variable override support (`PLONE_CLIENT_*`).
- JWT authentication via `/@login` / `/@logout` / `/@login-renew`.
- Static bearer-token support (skips login flow).
- Automatic retry with configurable exponential back-off.
- Typed exception hierarchy (`PloneAuthenticationError`, `PloneNotFoundError`, …).
- Customisable logging: `setup_logging()` + `set_logger()`.
- **Escape hatch**: `client.request(method, path, **kwargs)` + shorthand `get/post/patch/put/delete`.
- Resource managers:
  - `ContentManager` — CRUD, copy/move, workflow, lock, aliases, ordering.
  - `SearchManager` — `@search`, `@querystring-search`, lazy `iterate()`.
  - `UsersManager` / `GroupsManager` / `SharingManager`.
  - `RegistryManager` / `ControlpanelsManager` / `AddonsManager`.
  - `SiteManager` — types, vocabularies, roles, e-mail, undo.
  - `CommentsManager` / `HistoryManager` / `TilesManager`.
  - `FilesManager` — upload (base64 + TUS), download, image scales.
  - `RelationsManager` — `@relations`, `@brokenrelations`, `@relationstats`.
  - `WorkingCopyManager` — `@workingcopy` (plone.app.iterate).
  - `BlocksManager` — `@slots`, `@available-blocks`, `@blocksfield`.
  - `DatabaseManager` — ZODB stats, pack, catalog reindex/rebuild, link integrity.
- `pytest-docker` integration for end-to-end integration tests against a real Plone.
- PEP 561 `py.typed` marker.

[Unreleased]: https://github.com/yourorg/plone-client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourorg/plone-client/releases/tag/v0.1.0
