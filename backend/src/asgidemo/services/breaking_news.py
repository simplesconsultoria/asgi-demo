"""``@breaking-news``: a story's updates, newest first.

Updates come in the same shape as the websocket message, so the browser
renders one shape from both sources. The listing is also an expandable
component: ``GET <story>?expand=breaking-news`` carries the first page, which
lets Volto render it on the server with the content itself.
"""

from asgidemo.content.breaking_news import IBreakingNews
from asgidemo.live.messages import serialize
from plone.restapi.interfaces import IExpandableElement
from plone.restapi.services import Service
from typing import Any
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


DEFAULT_SIZE = 20
MAX_SIZE = 100


def _int(value: Any, default: int, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except TypeError, ValueError:
        return default
    number = max(number, 0)
    return min(number, maximum) if maximum is not None else number


def listing(story: Any, b_start: int = 0, b_size: int = DEFAULT_SIZE) -> dict:
    """A page of a story's updates, newest first.

    :param story: The ``BreakingNews`` story.
    :param b_start: Updates to skip.
    :param b_size: Updates to return.
    :returns: The story's UID, ``live`` flag, total, and the page of updates.
    """
    catalog = story.portal_catalog
    brains = catalog(
        portal_type="BreakingNewsUpdate",
        path={"query": "/".join(story.getPhysicalPath()), "depth": 1},
        sort_on="breaking_news_datetime",
        sort_order="descending",
    )
    total = len(brains)
    page = brains[b_start : b_start + b_size]
    return {
        "story": story.UID(),
        "live": bool(getattr(story, "live", False)),
        "items_total": total,
        "b_start": b_start,
        "b_size": b_size,
        "items": [serialize(brain.getObject(), story) for brain in page],
    }


@implementer(IExpandableElement)
@adapter(IBreakingNews, Interface)
class BreakingNewsUpdates:
    """The ``breaking-news`` component of a story."""

    def __init__(self, context: Any, request: Any) -> None:
        self.context = context
        self.request = request

    def __call__(self, expand: bool = False) -> dict:
        url = f"{self.context.absolute_url()}/@breaking-news"
        result = {"breaking-news": {"@id": url}}
        if not expand:
            return result
        form = self.request.form
        result["breaking-news"].update(
            listing(
                self.context,
                b_start=_int(form.get("b_start"), 0),
                b_size=_int(form.get("b_size"), DEFAULT_SIZE, MAX_SIZE),
            )
        )
        return result


class BreakingNewsGet(Service):
    """``GET <story>/@breaking-news?b_start=0&b_size=20``."""

    def reply(self) -> dict:
        return BreakingNewsUpdates(self.context, self.request)(expand=True)[
            "breaking-news"
        ]
