"""The websocket a reader opens on a story.

Connect order is load-bearing:

1. **Join** the hub first, so nothing published from then on can be missed.
   Nothing reaches the socket until it is accepted.
2. **Check and catch up** in one worker-thread hop, as the reader: find the
   story through the *restricted* catalog search, then send every update
   created since the page's cursor. An update committed between 1 and 2 is in
   the backlog, in the queue, or both; the client drops duplicates by UID.
3. **Accept** only after the object-level check. The route's ``permission``
   is checked on the portal, not on the story, so this check is the one that
   keeps a private story private.
"""

from AccessControl import Unauthorized
from asgidemo.live.hub import Closed
from asgidemo.live.messages import serialize
from DateTime import DateTime
from DateTime.interfaces import DateTimeError
from functools import partial
from ploneasgi import run_authenticated
from ploneasgi.context import SiteNotFound
from ploneasgi.vhm import SITE_KEY
from typing import Any

import anyio
import json
import logging
import re


logger = logging.getLogger("asgidemo.live")

CATCH_UP_LIMIT = 200
CLOCK_SKEW = 60  # seconds of overlap on the catch-up cursor

POLICY_VIOLATION = 1008
INTERNAL_ERROR = 1011

_UID = re.compile(r"[0-9a-f]{32}")


def _parse_since(value: str | None) -> DateTime | None:
    if not value:
        return None
    try:
        return DateTime(value)
    except DateTimeError, SyntaxError, ValueError:
        return None


def open_story(ctx: Any, uid: str, since: str | None) -> list[dict] | None:
    """Find a story as the reader and collect what they missed.

    Runs in a worker thread. Never use ``plone.app.uuid``'s ``uuidToObject``
    here: it traverses to the parent unrestricted and checks only the last
    step. The restricted catalog search plus ``ctx.traverse`` checks every
    step as the reader.

    :param ctx: The reader's Plone context.
    :param uid: The story's UID.
    :param since: ISO timestamp of the newest update the reader has, if any.
    :returns: The messages to send before going live, or ``None`` when the
        story does not exist or the reader may not see it (the two look the
        same from outside).
    """
    catalog = ctx.portal.portal_catalog
    # Calling the catalog is searchResults: the restricted search, filtered
    # on what this user may View.
    brains = catalog(UID=uid, portal_type="BreakingNews")
    if not brains:
        return None
    portal_path = "/".join(ctx.portal.getPhysicalPath())
    try:
        story = ctx.traverse(brains[0].getPath()[len(portal_path) + 1 :])
    except Unauthorized, KeyError, AttributeError:
        # Visible in the catalog but not reachable: a private folder on the way.
        return None

    cursor = _parse_since(since)
    if cursor is None:
        return []
    found = catalog(
        portal_type="BreakingNewsUpdate",
        path={"query": "/".join(story.getPhysicalPath()), "depth": 1},
        # created, not datetime: editors may back-date datetime. The overlap
        # absorbs clock skew between backends; the client de-duplicates.
        created={"query": cursor - CLOCK_SKEW / 86400, "range": "min"},
        sort_on="created",
        sort_limit=CATCH_UP_LIMIT + 1,
    )[: CATCH_UP_LIMIT + 1]
    if len(found) > CATCH_UP_LIMIT:
        return [{"v": 1, "kind": "reset", "story": uid}]
    return [serialize(brain.getObject(), story) for brain in found]


async def _pump(websocket: Any, subscriber: Any, cancel: anyio.CancelScope) -> None:
    """Send queued messages until the hub closes the subscriber."""
    try:
        while True:
            await websocket.send_text(await subscriber.next())
    except Closed as exc:
        await websocket.close(code=exc.code)
    except Exception:  # noqa: S110 - the client went away mid-send
        pass
    finally:
        cancel.cancel()


async def _drain_client(websocket: Any, cancel: anyio.CancelScope) -> None:
    """Read and ignore client frames, to notice a disconnect at once."""
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    finally:
        cancel.cancel()


async def breaking_news(websocket: Any) -> None:
    """Stream a story's updates to one reader.

    :param websocket: The Starlette websocket.
    """
    scope = websocket.scope
    hub = getattr(scope["app"].state, "breaking_news", None)
    uid = websocket.path_params["uid"]
    if hub is None:
        logger.error("Breaking News hub not running: is the lifespan installed?")
        await websocket.close(code=INTERNAL_ERROR)
        return
    if not _UID.fullmatch(uid):
        await websocket.close(code=POLICY_VIOLATION)
        return

    subscriber = hub.join(uid)
    try:
        try:
            backlog = await run_authenticated(
                scope,
                partial(open_story, uid=uid, since=websocket.query_params.get("since")),
                site_id=scope[SITE_KEY],
            )
        except SiteNotFound:
            backlog = None
        if backlog is None:
            await websocket.close(code=POLICY_VIOLATION)
            return

        await websocket.accept()
        for message in backlog:
            await websocket.send_text(json.dumps(message))

        async with anyio.create_task_group() as group:
            group.start_soon(_pump, websocket, subscriber, group.cancel_scope)
            group.start_soon(_drain_client, websocket, group.cancel_scope)
    finally:
        hub.leave(subscriber)
