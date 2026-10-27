"""Events fired by Breaking News stories.

Other consumers (mobile push, social posting) can subscribe to
:class:`IBreakingNewsUpdateAdded` without knowing about websockets.
"""

from typing import Any
from zope.interface import Attribute
from zope.interface import implementer
from zope.interface.interfaces import IObjectEvent
from zope.interface.interfaces import ObjectEvent


class IBreakingNewsUpdateAdded(IObjectEvent):
    """An update was added to a Breaking News story."""

    story = Attribute("The BreakingNews container.")


@implementer(IBreakingNewsUpdateAdded)
class BreakingNewsUpdateAdded(ObjectEvent):
    """An update landed in a story."""

    def __init__(self, obj: Any, story: Any) -> None:
        super().__init__(obj)
        self.story = story
