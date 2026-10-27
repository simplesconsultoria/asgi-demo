"""Breaking News Update: one update posted to a story."""

from asgidemo import _
from datetime import datetime
from datetime import UTC
from plone.app.textfield import RichText
from plone.dexterity.content import Item
from plone.supermodel import model
from typing import Any
from zope import schema
from zope.interface import implementer


def now_utc() -> datetime:
    """Default for an update's ``datetime`` field.

    :returns: The current time, timezone-aware, in UTC.
    """
    return datetime.now(UTC)


class IBreakingNewsUpdate(model.Schema):
    """One update posted to a Breaking News story."""

    datetime = schema.Datetime(
        title=_("Date and time"),
        description=_("Where the update sits on the story's timeline."),
        defaultFactory=now_utc,
        required=True,
    )

    body = RichText(
        title=_("Body"),
        required=False,
    )


@implementer(IBreakingNewsUpdate)
class BreakingNewsUpdate(Item):
    """An update inside a ``BreakingNews`` story."""


def store_datetime(update: BreakingNewsUpdate, event: Any) -> None:
    """Store the update's ``datetime`` when nobody set it.

    Dexterity answers an unset field with its default, computed on every
    read: an update created without a ``datetime`` would move along the
    timeline each time it is looked at.

    :param update: The update that was added.
    :param event: The ``IObjectAddedEvent``.
    """
    if "datetime" not in update.__dict__:
        update.datetime = now_utc()
