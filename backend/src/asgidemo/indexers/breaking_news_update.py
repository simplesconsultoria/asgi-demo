from asgidemo.content.breaking_news_update import IBreakingNewsUpdate
from datetime import datetime
from plone.indexer import indexer


@indexer(IBreakingNewsUpdate)
def breaking_news_datetime(obj: IBreakingNewsUpdate) -> datetime | None:
    """Index an update by its place on the story's timeline.

    :param obj: The update being indexed.
    :returns: The update's ``datetime`` field.
    """
    return obj.datetime
