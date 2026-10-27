"""Write messages to PostgreSQL in the same transaction as the ZODB commit.

PGJsonb lets a *state processor* run SQL at the end of the vote, on the
PostgreSQL transaction that carries the ZODB commit (``finalize(cursor)``).
:class:`OutboxProcessor` uses it to insert each pending message into
``breaking_news_outbox`` and ``NOTIFY`` its row id. PostgreSQL delivers a
notification only when its transaction commits, so:

* an aborted transaction, or a ``ConflictError`` retry, announces nothing;
* a committed update is always announced: there is no gap between the
  commit and a separate send that a crash could fall into.

The notification carries only the row id, which keeps it far below
PostgreSQL's 8000-byte payload limit; listeners read the message from the
outbox.

Messages are queued per transaction, on the transaction object itself, so
nothing can leak from one transaction into the next one on the same thread.
"""

from asgidemo import logger
from asgidemo.live import sql
from psycopg.types.json import Jsonb
from typing import Any

import transaction


class _Key:
    """Hashable key for :meth:`transaction.Transaction.data`."""


_KEY = _Key()


def pending(txn: Any = None, create: bool = False) -> list[dict]:
    """The messages queued on a transaction.

    :param txn: The transaction; the current one when omitted.
    :param create: Attach an empty list when none is there yet.
    :returns: The queued messages, oldest first; an empty list (not
        attached) when nothing is queued and ``create`` is false.
    """
    txn = txn or transaction.get()
    try:
        return txn.data(_KEY)
    except KeyError:
        queued: list[dict] = []
        if create:
            txn.set_data(_KEY, queued)
        return queued


def enqueue(message: dict, txn: Any = None) -> None:
    """Queue a message to be written when the transaction votes.

    :param message: The message, as built by
        :func:`asgidemo.live.messages.serialize`.
    :param txn: The transaction; the current one when omitted.
    """
    pending(txn, create=True).append(message)


class OutboxProcessor:
    """PGJsonb state processor that writes queued messages at vote time.

    It owns no ``object_state`` columns: ``process`` always answers
    ``None``, which leaves every row as it is.
    """

    def get_extra_columns(self) -> list:
        """:returns: No columns."""
        return []

    def process(self, zoid: int, class_mod: str, class_name: str, state: Any) -> None:
        """Leave the object's columns untouched.

        :returns: ``None``.
        """
        return None

    def get_schema_sql(self) -> str:
        """:returns: The outbox and presence tables."""
        return sql.SCHEMA

    def finalize(self, cursor: Any) -> None:
        """Insert and notify every message queued on the voting transaction.

        Runs on every commit, so it must cost nothing when nothing is queued.

        :param cursor: Cursor on the PostgreSQL transaction of the commit.
        """
        queued = pending()
        if not queued:
            return
        for message in queued:
            cursor.execute(
                sql.INSERT_AND_NOTIFY,
                {"story": message["story"], "payload": Jsonb(message)},
            )
        # Written: a second vote on this transaction must not write them twice.
        queued.clear()


def _main_storage(db: Any) -> Any:
    storage = db.storage
    return getattr(storage, "_main", storage)


def register_processor(event: Any) -> None:
    """``IDatabaseOpenedWithRoot`` subscriber: install the outbox processor.

    :param event: The event; ``event.database`` is the opened database.
    """
    storage = _main_storage(event.database)
    if not hasattr(storage, "register_state_processor"):
        logger.warning(
            "Storage %s is not PGJsonb: Breaking News updates will not be "
            "pushed to live readers.",
            type(storage).__name__,
        )
        return
    storage.register_state_processor(OutboxProcessor())
    logger.info("Registered the Breaking News outbox on %s", storage)
