"""Live Breaking News: updates pushed to readers over websockets.

Two halves, which never share a thread:

* The **Zope side** runs in the thread that commits. A new update fires
  :class:`~asgidemo.live.events.BreakingNewsUpdateAdded`; its subscriber builds
  the message before the commit, and the outbox processor writes it to
  PostgreSQL, with a ``NOTIFY``, inside the same PostgreSQL transaction as the
  ZODB commit (:mod:`asgidemo.live.outbox`).
* The **event-loop side** runs in each backend's ASGI process. One
  ``LISTEN`` connection per backend receives the notification, reads the
  message from the outbox and hands it to the websockets this backend holds
  (:mod:`asgidemo.live.hub`). No ZODB connection is involved after the commit.
"""
