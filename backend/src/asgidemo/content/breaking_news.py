"""Breaking News: a live story that collects updates as they happen."""

from asgidemo import _
from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class IBreakingNews(model.Schema):
    """A story that collects updates as they happen."""

    live = schema.Bool(
        title=_("Live"),
        description=_("Show the story as live and push new updates to readers."),
        default=True,
        required=False,
    )


@implementer(IBreakingNews)
class BreakingNews(Container):
    """Container of ``BreakingNewsUpdate`` items.

    A story that runs for days collects thousands of updates. The page sorts
    them by ``datetime`` and never uses folder order, so the container keeps
    none: adding an update does not rewrite an ordering list.
    """

    _ordering = "unordered"
