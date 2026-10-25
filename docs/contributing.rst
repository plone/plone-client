Contributing
============

Thank you for considering a contribution to plone-client!

.. contents::
   :local:
   :depth: 2


Development setup
-----------------

.. code-block:: bash

    git clone https://github.com/yourorg/plone-client
    cd plone-client
    python -m venv .venv
    source .venv/bin/activate
    make install          # installs package + dev deps
    make install-async    # also installs httpx


Code style
----------

We use **ruff** for linting and auto-formatting:

.. code-block:: bash

    make lint    # check
    make fmt     # auto-fix

All public API must have type annotations.  Check with:

.. code-block:: bash

    make typecheck


Testing
-------

Unit tests (no Docker, no network)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    make test-unit

Use ``responses`` (sync) and ``respx`` (async) to mock HTTP inside unit tests.
Never make real network calls from unit tests.

Integration tests (Docker required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    make test-integration

The integration suite uses ``pytest-docker`` to start
``plone/plone-backend:6`` automatically.  Override the image:

.. code-block:: bash

    PLONE_DOCKER_IMAGE=plone/plone-backend:6.1 make test-integration

Coverage report
~~~~~~~~~~~~~~~

.. code-block:: bash

    make coverage
    # opens htmlcov/index.html


Adding a new manager
--------------------

1. Create ``src/plone_client/managers/myfeature.py`` extending
   :class:`~plone_client.managers.base.BaseManager`.
2. Register it in ``managers/__init__.py``.
3. Add an attribute in :meth:`~plone_client.client.PloneClient._init_managers`
   in ``client.py``.
4. Optionally add an async counterpart in ``async_client.py`` by subclassing
   ``_AsyncBaseManager``.
5. Write unit tests using ``responses`` mocks.
6. Document the manager in ``docs/managers.rst``.
7. Update ``CHANGELOG.md`` under ``[Unreleased]``.


Submitting a pull request
--------------------------

1. Fork the repo and create a feature branch.
2. Write tests — PRs without tests will not be merged.
3. Run ``make lint typecheck test-unit`` — all must pass.
4. Update ``CHANGELOG.md`` under ``[Unreleased]``.
5. Open a PR with a clear description of what changed and why.


Reporting bugs
--------------

Open an issue at https://github.com/yourorg/plone-client/issues.

Please include:

- Python version
- Plone version
- plone.restapi version
- A minimal reproduction script
- The full traceback
