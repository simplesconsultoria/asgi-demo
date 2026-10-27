"""Fan-out from PostgreSQL to the websockets one backend holds.

Zope-free: everything here runs on the event loop. A socket costs a queue and
two small tasks, never a worker thread or a ZODB connection.

* :class:`Hub` is the in-process part: which sockets read which story, and
  what each of them is sent. It does no I/O, so it is tested on its own.
* :class:`PostgresBroker` connects the hub to PostgreSQL: one ``LISTEN``
  connection for notifications, one connection for reading messages and for
  presence, and the loops that keep both alive.
"""

from asgidemo.live import sql
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import asyncio
import json
import logging
import os
import random
import uuid


logger = logging.getLogger("asgidemo.live.hub")

# Close codes, from RFC 6455 and the IANA registry.
SERVICE_RESTART = 1012
TRY_AGAIN_LATER = 1013

QUEUE_SIZE = 256


def instance_id() -> str:
    """Identify this backend among the live ones.

    :returns: The container's ``HOSTNAME``, or a random id.
    """
    return os.environ.get("HOSTNAME") or uuid.uuid4().hex[:12]


class Closed(Exception):
    """The hub closed a subscriber; the socket must close with ``code``."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


class Subscriber:
    """One websocket's view of a story: a bounded queue of messages.

    :param story: UID of the story it reads.
    :param size: Messages it may fall behind before it is dropped.
    """

    def __init__(self, story: str, size: int = QUEUE_SIZE) -> None:
        self.story = story
        self.close_code: int | None = None
        self._queue: asyncio.Queue[str | None] = asyncio.Queue(size)

    def deliver(self, data: str) -> None:
        """Queue a message, or drop a reader that fell too far behind.

        A slow reader is closed with 1013 rather than buffered without bound:
        it reconnects and catches up from the catalog, which is cheaper.

        :param data: The message, JSON-encoded.
        """
        if self.close_code is not None:
            return
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            self.close(TRY_AGAIN_LATER)

    def close(self, code: int) -> None:
        """Ask the socket to close, ahead of anything still queued.

        :param code: The websocket close code to send.
        """
        if self.close_code is not None:
            return
        self.close_code = code
        while not self._queue.empty():
            self._queue.get_nowait()
        self._queue.put_nowait(None)

    async def next(self) -> str:
        """Wait for the next message.

        :returns: The message, JSON-encoded.
        :raises Closed: When the hub closed this subscriber.
        """
        data = await self._queue.get()
        if data is None:
            raise Closed(self.close_code or SERVICE_RESTART)
        return data


class Hub:
    """The sockets one backend holds, grouped by story.

    :param instance: This backend's id, for presence.
    """

    def __init__(self, instance: str) -> None:
        self.instance = instance
        self.local: dict[str, set[Subscriber]] = {}

    def join(self, story: str) -> Subscriber:
        """Register a socket for a story's messages.

        :param story: The story's UID.
        :returns: The socket's subscriber.
        """
        subscriber = Subscriber(story)
        self.local.setdefault(story, set()).add(subscriber)
        return subscriber

    def leave(self, subscriber: Subscriber) -> None:
        """Forget a socket.

        :param subscriber: What :meth:`join` returned.
        """
        peers = self.local.get(subscriber.story, set())
        peers.discard(subscriber)
        if not peers:
            self.local.pop(subscriber.story, None)

    def deliver(self, story: str, data: str) -> int:
        """Hand a message to every local reader of a story.

        :param story: The story's UID.
        :param data: The message, JSON-encoded.
        :returns: How many readers it was handed to.
        """
        peers = tuple(self.local.get(story, ()))
        for subscriber in peers:
            subscriber.deliver(data)
        return len(peers)

    def close_all(self, code: int) -> None:
        """Close every local socket, so its client reconnects and catches up.

        :param code: The websocket close code to send.
        """
        for peers in self.local.values():
            for subscriber in peers:
                subscriber.close(code)

    def counts(self) -> dict[str, int]:
        """:returns: Local readers per story."""
        return {story: len(peers) for story, peers in self.local.items()}


def presence_message(story: str, readers: int) -> str:
    """Build the message that tells readers how many others are reading.

    :param story: The story's UID.
    :param readers: Readers across every backend.
    :returns: The message, JSON-encoded.
    """
    return json.dumps({"v": 1, "kind": "presence", "story": story, "readers": readers})


def backoff(attempt: int, cap: float = 30.0) -> float:
    """Full-jitter delay before reconnect attempt ``attempt``.

    :param attempt: Failed attempts so far, from 0.
    :param cap: Longest delay, in seconds.
    :returns: Seconds to wait.
    """
    return random.uniform(0, min(cap, 0.5 * 2**attempt))  # noqa: S311


Connect = Callable[..., Awaitable[Any]]


def _default_connect() -> Connect:
    import psycopg

    return psycopg.AsyncConnection.connect


class PostgresBroker:
    """Connect a :class:`Hub` to PostgreSQL.

    :param dsn: libpq connection string.
    :param hub: The hub to feed.
    :param presence_interval: Seconds between presence reports.
    :param presence_expiry: Seconds after which a backend's report no longer
        counts; a backend that died drops out of the total after this.
    :param outbox_keep: Seconds an outbox row is kept.
    :param connect: Opens an async connection; injectable for tests.
    """

    def __init__(
        self,
        dsn: str,
        hub: Hub,
        *,
        presence_interval: float = 5.0,
        presence_expiry: float = 15.0,
        outbox_keep: float = 24 * 3600.0,
        connect: Connect | None = None,
    ) -> None:
        self.dsn = dsn
        self.hub = hub
        self.presence_interval = presence_interval
        self.presence_expiry = presence_expiry
        self.outbox_keep = outbox_keep
        self._connect = connect or _default_connect()
        self._conn: Any = None
        self._conn_lock = asyncio.Lock()

    async def _query_connection(self) -> Any:
        """The connection for reads and presence, reopened when it broke."""
        async with self._conn_lock:
            if self._conn is None or self._conn.closed:
                self._conn = await self._connect(self.dsn, autocommit=True)
            return self._conn

    async def _execute(self, query: str, params: dict | None = None) -> list:
        conn = await self._query_connection()
        try:
            cursor = await conn.execute(query, params)
            return await cursor.fetchall() if cursor.description else []
        except Exception:
            # Reopen on the next call; the caller decides what to do now.
            await self._discard_connection()
            raise

    async def _discard_connection(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            # Already broken: closing it is a courtesy.
            with suppress(Exception):
                await conn.close()

    async def ensure_schema(self) -> None:
        """Create the outbox and presence tables if they are missing."""
        await self._execute(sql.SCHEMA)

    async def fetch(self, message_id: int) -> dict | None:
        """Read one message from the outbox.

        :param message_id: The row id the notification carried.
        :returns: The message, or ``None`` when the row is gone.
        """
        rows = await self._execute(sql.SELECT_MESSAGE, {"id": message_id})
        return rows[0][0] if rows else None

    async def handle_notification(self, payload: str) -> None:
        """Deliver the message a notification points to.

        :param payload: The notification payload: an outbox row id.
        """
        try:
            message_id = int(payload)
        except ValueError:
            logger.warning("ignoring notification with payload %r", payload)
            return
        message = await self.fetch(message_id)
        if message is None:
            return
        delivered = self.hub.deliver(message["story"], json.dumps(message))
        logger.debug("message %s delivered to %d reader(s)", message_id, delivered)

    async def listen_forever(self) -> None:
        """Hold the ``LISTEN`` connection, reconnecting with backoff.

        Each time it subscribes again after a failure, every local socket is
        closed with 1012: notifications sent while it was away are lost, and
        closing makes each client reconnect and catch up from the catalog.
        """
        attempt = 0
        subscribed_before = False
        while True:
            try:
                conn = await self._connect(self.dsn, autocommit=True)
                async with conn:
                    await conn.execute(sql.LISTEN)
                    if subscribed_before:
                        self.hub.close_all(SERVICE_RESTART)
                    subscribed_before = True
                    attempt = 0
                    logger.info("listening on channel %s", sql.CHANNEL)
                    async for notification in conn.notifies():
                        try:
                            await self.handle_notification(notification.payload)
                        except Exception:
                            logger.exception(
                                "could not deliver %s", notification.payload
                            )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                delay = backoff(attempt)
                attempt += 1
                logger.warning(
                    "LISTEN connection lost (%s); retrying in %.1fs", exc, delay
                )
                await asyncio.sleep(delay)

    async def report_presence(self) -> None:
        """Report this backend's readers and push the totals to them."""
        counts = self.hub.counts()
        for story, readers in counts.items():
            await self._execute(
                sql.REPORT_PRESENCE,
                {"backend": self.hub.instance, "story": story, "readers": readers},
            )
        stories = list(counts)
        await self._execute(
            sql.FORGET_PRESENCE, {"backend": self.hub.instance, "stories": stories}
        )
        if not stories:
            return
        rows = await self._execute(
            sql.TOTAL_PRESENCE, {"stories": stories, "expiry": self.presence_expiry}
        )
        for story, readers in rows:
            self.hub.deliver(story, presence_message(story, readers))

    async def presence_forever(self) -> None:
        """Report presence every ``presence_interval`` seconds."""
        while True:
            try:
                await self.report_presence()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("could not report presence: %s", exc)
            await asyncio.sleep(self.presence_interval)

    async def prune_forever(self, interval: float = 600.0) -> None:
        """Delete old outbox rows and stale presence reports.

        :param interval: Seconds between runs.
        """
        while True:
            try:
                await self._execute(sql.PRUNE_OUTBOX, {"keep": self.outbox_keep})
                await self._execute(sql.PRUNE_PRESENCE, {"keep": 3600})
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("could not prune: %s", exc)
            await asyncio.sleep(interval)

    async def run(self) -> None:
        """Run every loop until cancelled."""
        attempt = 0
        while True:
            try:
                await self.ensure_schema()
                break
            except Exception as exc:
                delay = backoff(attempt)
                attempt += 1
                logger.warning(
                    "PostgreSQL not ready (%s); retrying in %.1fs", exc, delay
                )
                await asyncio.sleep(delay)
        async with asyncio.TaskGroup() as group:
            group.create_task(self.listen_forever())
            group.create_task(self.presence_forever())
            group.create_task(self.prune_forever())

    async def aclose(self) -> None:
        """Close the query connection."""
        await self._discard_connection()
