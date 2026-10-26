---
myst:
  html_meta:
    "description": "The exceptions plone-client raises, and the HTTP status codes they stand for."
    "property=og:description": "The exceptions plone-client raises, and the HTTP status codes they stand for."
    "property=og:title": "Exceptions"
---

(reference-exceptions)=

# Exceptions

Every exception derives from {class}`~plone_client.exceptions.PloneClientError`, and every one is importable from `plone_client`.

## Hierarchy

<!-- source: src/plone_client/exceptions.py -->

| Exception | Parent | Raised when | CLI exit code |
|---|---|---|---|
| {class}`~plone_client.exceptions.PloneClientError` | `Exception` | Base of all the others. | 1 |
| {class}`~plone_client.exceptions.PloneConfigurationError` | `PloneClientError` | A profile, a secret, or the URL is missing or invalid. | 3 |
| {class}`~plone_client.exceptions.PloneReadOnlyError` | `PloneClientError` | A read-only client is asked to change the site. | 7 |
| {class}`~plone_client.exceptions.PloneConnectionError` | `PloneClientError` | The site cannot be reached. | 8 |
| {class}`~plone_client.exceptions.PloneTimeoutError` | `PloneConnectionError` | The site does not answer in time. | 8 |
| {class}`~plone_client.exceptions.PloneAPIError` | `PloneClientError` | The site answers with an error not listed below. | 1 |
| {class}`~plone_client.exceptions.PloneBadRequestError` | `PloneAPIError` | `400` | 6 |
| {class}`~plone_client.exceptions.PloneAuthenticationError` | `PloneAPIError` | `401` | 4 |
| {class}`~plone_client.exceptions.PloneForbiddenError` | `PloneAPIError` | `403`, also for a locked item | 4 |
| {class}`~plone_client.exceptions.PloneNotFoundError` | `PloneAPIError` | `404` | 5 |
| {class}`~plone_client.exceptions.PloneConflictError` | `PloneAPIError` | `409` | 6 |
| {class}`~plone_client.exceptions.PloneServerError` | `PloneAPIError` | `5xx` | 9 |

## Attributes of `PloneAPIError`

| Attribute | Meaning |
|---|---|
| `status_code` | HTTP status of the answer. |
| `error_type` | The error type `plone.restapi` reports, such as `NotFound` or `BadRequest`. |
| `message` | The error message `plone.restapi` reports. |
| `method` | Method of the request. |
| `url` | URL of the request. |
| `body` | The decoded body of the answer. |

## Classes

```{eval-rst}
.. automodule:: plone_client.exceptions
```

## Related

- {ref}`howto-handle-errors` catches and reports these errors.
- {ref}`reference-cli` lists the exit codes of the command line.
