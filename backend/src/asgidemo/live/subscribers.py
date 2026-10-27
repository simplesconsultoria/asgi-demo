"""From Zope events to the outbox."""

from asgidemo.live import outbox
from asgidemo.live.events import BreakingNewsUpdateAdded
from asgidemo.live.messages import serialize
from typing import Any
from zope.event import notify

import transaction


def update_added(update: Any, event: Any) -> None:
    """``IObjectAddedEvent`` on an update: fire our own event.

    :param update: The update that was added.
    :param event: The container event; ``newParent`` is the story.
    """
    if event.newParent is None:
        return
    notify(BreakingNewsUpdateAdded(update, event.newParent))


def announce(update: Any, event: Any) -> None:
    """Queue the update's message for the outbox, built at commit time.

    The message is built in a before-commit hook rather than here: depending
    on the add path (a form, the REST API, a script), fields may be set after
    ``IObjectAddedEvent`` fires, and the hook reads the object once everything
    in the request has run. The outbox processor then writes it during the
    vote, so only a transaction that commits announces anything.

    :param update: The update that was added.
    :param event: The :class:`BreakingNewsUpdateAdded` event.
    """
    txn = transaction.get()
    story = event.story

    def build() -> None:
        outbox.enqueue(serialize(update, story), txn)

    txn.addBeforeCommitHook(build)
