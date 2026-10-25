Quick Start
===========

Connect and authenticate
-------------------------

.. code-block:: python

    from plone_client import PloneClient

    # Credentials in code (fine for scripts; use env vars in production)
    with PloneClient(
        base_url="https://my.plone.site",
        username="admin",
        password="secret",
    ) as client:
        info = client.site.info()
        print(info["title"])

Using environment variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set ``PLONE_CLIENT_BASE_URL``, ``PLONE_CLIENT_USERNAME``, and
``PLONE_CLIENT_PASSWORD`` then simply call:

.. code-block:: python

    with PloneClient() as client:   # reads from env
        ...

See :doc:`configuration` for the full list of supported variables.


Create, read, update, delete
-----------------------------

.. code-block:: python

    with PloneClient() as client:

        # Create a Document in the site root
        doc = client.content.create(
            "/",
            "Document",
            title="Hello World",
            description="My first page",
        )
        path = doc["@id"].replace(client.config.base_url, "")

        # Read it back
        page = client.content.get(path)
        print(page["title"])          # Hello World

        # Update a field
        client.content.update(path, description="Updated!")

        # Publish it
        client.content.transition(path, "publish")

        # Delete
        client.content.delete(path)


Search
------

.. code-block:: python

    results = client.search.search(
        {"portal_type": "Document", "review_state": "published"},
        sort_on="effective",
        sort_order="descending",
        b_size=20,
    )
    print(f"{results['items_total']} results")
    for item in results["items"]:
        print(item["@id"], item["title"])


Lazy iteration over large result sets
--------------------------------------

.. code-block:: python

    for item in client.search.iterate({"portal_type": "News Item"}):
        # Pages through all results automatically; never loads everything
        process(item)


File upload
-----------

.. code-block:: python

    # Upload from a path
    file_obj = client.files.upload("/documents", "report.pdf", "/tmp/report.pdf")

    # Or from bytes
    client.files.upload("/images", "logo.png", png_bytes, content_type="image/png")

    # Download back
    data = client.files.download("/documents/report-pdf")


Custom / add-on endpoints (escape hatch)
-----------------------------------------

.. code-block:: python

    # Raw response — you control parsing
    response = client.request("GET", "/@my-addon-endpoint", params={"q": "foo"})
    data = response.json()

    # Shorthand verbs
    client.post("/@my-action", json={"key": "value"})
