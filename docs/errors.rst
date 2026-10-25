Error Handling
==============

All exceptions raised by plone-client inherit from
:class:`~plone_client.exceptions.PloneClientError`, so you can always use a
single ``except PloneClientError`` to catch everything.


Exception hierarchy
--------------------

.. code-block:: text

    PloneClientError                ← base; catch-all
    ├── PloneAuthenticationError    ← HTTP 401
    ├── PloneForbiddenError         ← HTTP 403
    ├── PloneNotFoundError          ← HTTP 404
    ├── PloneConflictError          ← HTTP 409 (duplicate id, etc.)
    ├── PloneServerError            ← HTTP 5xx
    ├── PloneConnectionError        ← TCP / network failures
    ├── PloneTimeoutError           ← request timeout (after all retries)
    └── PloneAPIError               ← any other unexpected status code
            .status_code            ← int | None
            .response_body          ← parsed JSON or raw text


Importing exceptions
--------------------

.. code-block:: python

    from plone_client import (
        PloneClientError,           # base
        PloneAuthenticationError,
        PloneForbiddenError,
        PloneNotFoundError,
        PloneConflictError,
        PloneServerError,
        PloneConnectionError,
        PloneTimeoutError,
        PloneAPIError,
    )


Typical error handling pattern
--------------------------------

.. code-block:: python

    from plone_client import (
        PloneClient,
        PloneNotFoundError,
        PloneForbiddenError,
        PloneAuthenticationError,
        PloneServerError,
        PloneClientError,
    )

    with PloneClient() as client:
        try:
            doc = client.content.get("/my/path")

        except PloneNotFoundError:
            print("Content not found")

        except PloneForbiddenError:
            print("No permission")

        except PloneAuthenticationError:
            print("Session expired — re-login")
            client.login()

        except PloneServerError as exc:
            print(f"Plone server error: {exc}")

        except PloneClientError as exc:
            # Catches everything else (timeout, connection, unexpected status)
            print(f"Unexpected error: {exc}")


PloneAPIError — accessing metadata
------------------------------------

:class:`~plone_client.exceptions.PloneAPIError` is raised for any unexpected
HTTP status code (e.g. ``422 Unprocessable Entity`` from a schema validation
failure).  It carries the original status code and parsed response body:

.. code-block:: python

    from plone_client import PloneAPIError

    try:
        client.content.create("/", "Document", title="")
    except PloneAPIError as exc:
        print(exc.status_code)      # e.g. 400
        print(exc.response_body)    # parsed JSON dict or raw string


Connection and timeout errors
-------------------------------

These are raised after all configured retries have been exhausted:

.. code-block:: python

    from plone_client import PloneTimeoutError, PloneConnectionError

    try:
        result = client.content.get("/slow-endpoint")
    except PloneTimeoutError:
        print("Timed out after all retries")
    except PloneConnectionError:
        print("Cannot reach the server")


API reference
-------------

.. automodule:: plone_client.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
