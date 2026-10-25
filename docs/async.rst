Async Client
============

:class:`~plone_client.async_client.AsyncPloneClient` is a full async counterpart
of :class:`~plone_client.PloneClient` backed by `httpx`_.

.. _httpx: https://www.python-httpx.org/


Installation
------------

The async support is an optional extra:

.. code-block:: bash

    pip install "plone-client[async]"


Basic usage
-----------

.. code-block:: python

    import asyncio
    from plone_client.async_client import AsyncPloneClient

    async def main():
        async with AsyncPloneClient(
            base_url="https://my.plone.site",
            username="admin",
            password="secret",
        ) as client:
            doc = await client.content.get("/front-page")
            print(doc["title"])

    asyncio.run(main())


Concurrent fetches
------------------

One of the main benefits of the async client is running multiple requests
in parallel with :func:`asyncio.gather`:

.. code-block:: python

    async def fetch_many(client, paths):
        tasks = [client.content.get(p) for p in paths]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def main():
        async with AsyncPloneClient() as client:
            pages = await fetch_many(client, ["/news", "/events", "/about"])
            for page in pages:
                if isinstance(page, Exception):
                    print(f"Error: {page}")
                else:
                    print(page["title"])


Async lazy iteration
---------------------

:meth:`~plone_client.async_client.AsyncSearchManager.iterate` is an
**async generator** that pages through large result sets without loading
everything into memory:

.. code-block:: python

    async with AsyncPloneClient() as client:
        async for item in client.search.iterate({"portal_type": "Document"}):
            await process_item(item)

You can also collect all items as a list:

.. code-block:: python

    items = [item async for item in client.search.iterate()]


Available async managers
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Attribute
     - Description
   * - ``client.content``
     - :class:`~plone_client.async_client.AsyncContentManager` — CRUD, copy/move, workflow
   * - ``client.search``
     - :class:`~plone_client.async_client.AsyncSearchManager` — search, querystring, async iterate
   * - ``client.users``
     - :class:`~plone_client.async_client.AsyncUsersManager` — user CRUD, my-information

Additional async managers can be added by subclassing
:class:`~plone_client.async_client._AsyncBaseManager` and registering them in
:meth:`~plone_client.async_client.AsyncPloneClient._init_managers`.


Async escape hatch
------------------

.. code-block:: python

    async with AsyncPloneClient() as client:
        response = await client.request("GET", "/@my-custom-endpoint")
        data = response.json()


API reference
-------------

.. autoclass:: plone_client.async_client.AsyncPloneClient
   :members:
   :undoc-members:

.. autoclass:: plone_client.async_client.AsyncContentManager
   :members:
   :undoc-members:

.. autoclass:: plone_client.async_client.AsyncSearchManager
   :members:
   :undoc-members:

.. autoclass:: plone_client.async_client.AsyncUsersManager
   :members:
   :undoc-members:
