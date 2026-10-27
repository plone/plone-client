---
myst:
  html_meta:
    "description": "The managers of PloneClient and the plone.restapi services each one calls."
    "property=og:description": "The managers of PloneClient and the plone.restapi services each one calls."
    "property=og:title": "Managers"
---

(reference-managers)=

# Managers

Each {class}`~plone_client.PloneClient` has one manager per group of `plone.restapi` services, as an attribute.

## Attributes and services

<!-- source: src/plone_client/client.py, src/plone_client/managers/ -->

| Attribute | Class | Services |
|---|---|---|
| `content` | {class}`~plone_client.managers.content.ContentManager` | content CRUD, `@copy`, `@move`, `@lock`, `@linkintegrity`, ordering |
| `search` | {class}`~plone_client.managers.search.SearchManager` | `@search` |
| `querystring` | {class}`~plone_client.managers.search.QuerystringManager` | `@querystring`, `@querystring-search` |
| `workflow` | {class}`~plone_client.managers.workflow.WorkflowManager` | `@workflow` |
| `history` | {class}`~plone_client.managers.workflow.HistoryManager` | `@history` |
| `working_copy` | {class}`~plone_client.managers.workflow.WorkingCopyManager` | `@workingcopy` |
| `files` | {class}`~plone_client.managers.files.FilesManager` | file and image fields, `@tus-upload`, `@tus-replace`, `@@download`, image scales |
| `navigation` | {class}`~plone_client.managers.navigation.NavigationManager` | `@navigation`, `@breadcrumbs`, `@contextnavigation`, `@navroot`, `@actions`, `@inherit` |
| `aliases` | {class}`~plone_client.managers.discussion.AliasesManager` | `@aliases` |
| `comments` | {class}`~plone_client.managers.discussion.CommentsManager` | `@comments` |
| `translations` | {class}`~plone_client.managers.discussion.TranslationsManager` | `@translations`, `@translation-locator` |
| `relations` | {class}`~plone_client.managers.discussion.RelationsManager` | `@relations` |
| `users` | {class}`~plone_client.managers.users.UsersManager` | `@users`, `@userschema`, `@portrait` |
| `groups` | {class}`~plone_client.managers.users.GroupsManager` | `@groups` |
| `sharing` | {class}`~plone_client.managers.users.SharingManager` | `@sharing`, `@principals`, `@roles` |
| `types` | {class}`~plone_client.managers.types.TypesManager` | `@types` |
| `block_types` | {class}`~plone_client.managers.block_types.BlockTypesManager` | `@blocks-schema` of the Volto server, at `frontend_url` |
| `vocabularies` | {class}`~plone_client.managers.types.VocabulariesManager` | `@vocabularies`, `@sources`, `@querysources` |
| `registry` | {class}`~plone_client.managers.site.RegistryManager` | `@registry` |
| `controlpanels` | {class}`~plone_client.managers.site.ControlpanelsManager` | `@controlpanels` |
| `addons` | {class}`~plone_client.managers.site.AddonsManager` | `@addons` |
| `content_rules` | {class}`~plone_client.managers.site.ContentRulesManager` | `@content-rules` |
| `system` | {class}`~plone_client.managers.site.SystemManager` | `@site`, `@system`, `@database`, `@transactions`, `@upgrade`, `GET @login`, `@email-send`, `@email-notification` |

## Item references

Every method that takes an item accepts any of these forms.

| Form | Example |
|---|---|
| Path from the site root | `/news/hello` |
| URL inside the site | `https://example.org/news/hello` |
| UID reference | `uid:a2c1e1e88b3e4c3c8f0a1e2d3c4b5a69` |
| `resolveuid` link | `../resolveuid/a2c1e1e88b3e4c3c8f0a1e2d3c4b5a69` |

A UID reference costs one extra `@search` request.
A URL outside the site raises {class}`ValueError`.

(reference-managers-block-types)=

## Block types

`client.block_types` asks the `@blocks-schema` service of the Volto server, which lists the blocks a site offers with their documentation, data schema, and variations.
Volto serves it, not `plone.restapi`, so the request goes to the client's `frontend_url`, without `++api++`, and with a Bearer token.
A client that uses basic authentication gets the token from `@login` once.

When the site cannot answer, the manager describes Volto's core blocks instead, from documentation that ships with plone-client.
Its answer then has `"source": "builtin"`, a `warning` that says why, and no `schema`.

| Situation | Answer |
|---|---|
| The service answers | The site's own answer, with `"source": "site"`. |
| `frontend_url` serves an HTML page, as a Volto without the service does | Builtin. |
| `frontend_url` answers `404`, as the backend does | Builtin. |
| `frontend_url` cannot be reached | Builtin. |
| The client is anonymous, and the service answers `401` | Builtin. |
| The service refuses the token with `401` | {class}`~plone_client.exceptions.PloneAuthenticationError` |
| The service answers `404` for one block, but lists blocks | {class}`~plone_client.exceptions.PloneNotFoundError` |
| A builtin answer for a block that is not a core block | {class}`~plone_client.exceptions.PloneNotFoundError` |

The core blocks are `slate`, `title`, `description`, `image`, `teaser`, `listing`, `gridBlock`, `search`, `video`, `maps`, `html`, `toc`, and `detachedSlate`.
Their documentation comes from Volto, under the MIT license.

## Classes

```{eval-rst}
.. automodule:: plone_client.managers.base
.. automodule:: plone_client.managers.content
.. automodule:: plone_client.managers.search
.. automodule:: plone_client.managers.workflow
.. automodule:: plone_client.managers.files
.. automodule:: plone_client.managers.navigation
.. automodule:: plone_client.managers.discussion
.. automodule:: plone_client.managers.users
.. automodule:: plone_client.managers.types
.. automodule:: plone_client.managers.block_types
.. automodule:: plone_client.managers.site
```

## Related

- {ref}`reference-compatibility` lists the services that need a newer `plone.restapi`.
- {ref}`howto-call-other-services` reaches services without a manager.
