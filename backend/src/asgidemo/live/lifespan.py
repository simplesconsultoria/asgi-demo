"""Start and stop the hub with the server.

An add-on cannot register a lifespan from ZCML, so the project's server
script passes :func:`breaking_news_lifespan` to ``create_app(lifespans=...)``.
"""

from asgidemo.live.hub import Hub
from asgidemo.live.hub import instance_id
from asgidemo.live.hub import PostgresBroker
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Any

import asyncio
import logging
import os


logger = logging.getLogger("asgidemo.live")


def broker_dsn() -> str | None:
    """The PostgreSQL the hub listens on.

    :returns: ``BREAKING_NEWS_DSN``, else the ZODB's ``ZODB_PGJSONB_DSN``,
        else ``None``.
    """
    return os.environ.get("BREAKING_NEWS_DSN") or os.environ.get("ZODB_PGJSONB_DSN")


@asynccontextmanager
async def breaking_news_lifespan(app: Any) -> AsyncIterator[None]:
    """Run the hub and its PostgreSQL loops for the server's lifetime.

    :param app: The Starlette application; the hub is published on
        ``app.state.breaking_news``.
    :yields: Control for the lifetime of the server.
    """
    hub = Hub(instance_id())
    app.state.breaking_news = hub
    dsn = broker_dsn()
    if not dsn:
        logger.warning(
            "No BREAKING_NEWS_DSN or ZODB_PGJSONB_DSN: live updates only reach "
            "readers on this backend, and only after they reconnect."
        )
        yield
        return
    broker = PostgresBroker(dsn, hub)
    task = asyncio.create_task(broker.run(), name="breaking-news-broker")
    logger.info("Breaking News hub %s started", hub.instance)
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await broker.aclose()
