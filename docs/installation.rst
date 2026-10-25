Installation
============

Requirements
------------

- Python 3.10 or newer
- A running Plone site with `plone.restapi`_ installed

.. _plone.restapi: https://pypi.org/project/plone.restapi/


Stable release
--------------

.. code-block:: bash

    pip install plone-client


Async support
-------------

The async extra pulls in `httpx`_ for :class:`~plone_client.AsyncPloneClient`:

.. code-block:: bash

    pip install "plone-client[async]"

.. _httpx: https://www.python-httpx.org/


Development install
-------------------

.. code-block:: bash

    git clone https://github.com/yourorg/plone-client
    cd plone-client
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev,async]"


Verify
------

.. code-block:: python

    import plone_client
    print(plone_client.__version__)
