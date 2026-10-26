---
myst:
  html_meta:
    "description": "Why plone-client is one synchronous client per site, organized in managers, and how it treats retries and item references."
    "property=og:description": "Why plone-client is one synchronous client per site, organized in managers, and how it treats retries and item references."
    "property=og:title": "About the design of plone-client"
---

(explanation-design)=

# About the design of plone-client

plone-client is built for two kinds of work: code that moves content into or around a Plone site, and people or agents managing a site from a terminal.
Both need the same thing underneath, a faithful and predictable way to speak `plone.restapi`.
This page explains the choices that follow from that.

## One client per site

A {class}`~plone_client.PloneClient` holds everything about one site: its URL, its credentials, its HTTP connections, and its safety switches.
There is no global configuration and no default site.

That makes the common case of working with several sites at once ordinary.
A migration reads from one client and writes through another, and nothing either client does can leak into the other.

## Managers mirror `plone.restapi`

The managers follow `plone.restapi`'s own grouping of services, so the documentation of an endpoint and the method that calls it are easy to find from each other.
For example, `client.workflow` calls `@workflow`, and `client.sharing` calls `@sharing`.

Each method sends exactly what `plone.restapi` documents, and returns what the site answers, decoded but otherwise untouched.
plone-client adds no object model on top of the JSON.
A model would have to follow every content type and every add-on a site has, and it would always lag behind the site itself.

## Any reference to an item

Content arrives from many places: a path typed by a person, an `@id` from an earlier answer, a UID stored in a relation field, or a `resolveuid` link inside a block.
Every method that takes an item accepts all of them, so code does not have to convert one into another first.
A UID costs one extra search, which is the price of not having to know the path.

## Synchronous, on purpose

plone-client is synchronous.
The work it is meant for is sequential by nature: create a folder, then the pages inside it, then publish them.
A Plone site also serializes writes to the same objects, so sending many changes at once rarely makes a sync faster and often makes it fail with conflicts.

A synchronous client keeps scripts simple to read, to debug, and to stop halfway.
The library is built on [httpx](https://www.python-httpx.org), which keeps an asynchronous version possible later without changing how requests are built.

## Retries that never repeat a change

Sites behind proxies sometimes answer `502`, `503`, or `504` for a moment, or ask clients to slow down with `429`.
plone-client retries those answers, but only for requests that are safe to repeat: reads, `PUT`, and `DELETE`.

A `POST` that timed out may have created the item before the answer was lost.
Retrying it could create a second one, so plone-client lets the error reach your code instead, which can check whether the item exists.

## Errors carry the site's words

When a site refuses a request, `plone.restapi` explains why in the body of the answer.
plone-client turns each status into its own exception class, so code can catch exactly the case it handles, and keeps the type and message `plone.restapi` sent, so the reason reaches the person reading the error.

## Related

- {ref}`reference-managers` lists the managers and their services.
- {ref}`reference-client` describes the retries in detail.
