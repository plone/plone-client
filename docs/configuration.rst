Configuration
=============

All settings can be passed as keyword arguments to :class:`~plone_client.PloneClient`
or :class:`~plone_client.PloneClientConfig`, **or** provided as environment variables.
Programmatic values always take precedence over environment variables.


Environment variables
---------------------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Variable
     - Default
     - Description
   * - ``PLONE_CLIENT_BASE_URL``
     - —
     - Root URL of the Plone site (required)
   * - ``PLONE_CLIENT_USERNAME``
     - —
     - Username for JWT authentication
   * - ``PLONE_CLIENT_PASSWORD``
     - —
     - Password for JWT authentication
   * - ``PLONE_CLIENT_TOKEN``
     - —
     - Pre-issued bearer token (skips login)
   * - ``PLONE_CLIENT_TIMEOUT``
     - ``30``
     - Request timeout in seconds
   * - ``PLONE_CLIENT_VERIFY_SSL``
     - ``true``
     - Set ``false`` / ``0`` / ``no`` to disable SSL verification
   * - ``PLONE_CLIENT_MAX_RETRIES``
     - ``3``
     - Number of automatic retries on transient errors
   * - ``PLONE_CLIENT_RETRY_BACKOFF``
     - ``0.5``
     - Exponential back-off multiplier (sleep = backoff × 2^attempt)
   * - ``PLONE_CLIENT_LOG_LEVEL``
     - ``WARNING``
     - One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``


Programmatic configuration
--------------------------

.. code-block:: python

    from plone_client import PloneClient, PloneClientConfig

    cfg = PloneClientConfig(
        base_url="https://my.plone.site",
        username="admin",
        password="secret",
        timeout=60.0,
        verify_ssl=True,
        max_retries=5,
        retry_backoff=1.0,
        log_level="INFO",
    )

    with PloneClient(config=cfg) as client:
        ...

You can also pass keyword arguments directly to :class:`~plone_client.PloneClient`:

.. code-block:: python

    with PloneClient(
        base_url="https://my.plone.site",
        username="admin",
        password="secret",
        max_retries=5,
    ) as client:
        ...


Static bearer token
-------------------

If you already have a JWT or bearer token (e.g. from SSO or a pre-auth step),
pass it via ``token=`` to skip the login flow entirely:

.. code-block:: python

    with PloneClient(base_url="https://my.plone.site", token="my-jwt-token") as client:
        # No POST /@login is performed
        ...

You can also set ``PLONE_CLIENT_TOKEN`` in the environment.


Token renewal
-------------

JWT tokens issued by Plone expire after a configurable period.
Call :meth:`~plone_client.PloneClient.renew_token` before the token expires:

.. code-block:: python

    client.renew_token()   # POST /@login-renew


Retry policy
------------

Failed requests are automatically retried with exponential back-off:

.. code-block:: text

    sleep = retry_backoff × (2 ^ attempt)

    attempt 0: immediate
    attempt 1: sleep 0.5s   (backoff=0.5)
    attempt 2: sleep 1.0s
    attempt 3: sleep 2.0s

Retries happen on:

- Network timeouts (any method)
- TCP connection failures (any method)
- HTTP ``429``, ``500``, ``502``, ``503``, ``504`` for **idempotent** methods
  (``GET``, ``HEAD``, ``OPTIONS``, ``DELETE``)

Non-idempotent methods (``POST``, ``PATCH``, ``PUT``) are **not** retried on 5xx
to avoid accidental duplicate writes.

Set ``max_retries=0`` to disable retries entirely.


SSL verification
----------------

Disable SSL verification in development environments:

.. code-block:: python

    PloneClientConfig(base_url="https://dev.local", verify_ssl=False)

Or via environment:

.. code-block:: bash

    PLONE_CLIENT_VERIFY_SSL=false python my_script.py

.. warning::

   Never disable SSL verification in production.
