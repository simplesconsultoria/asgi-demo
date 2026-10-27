"""The message a reader receives for one update.

The message carries the whole update, not only its UID. A backend that
receives it never reads the ZODB to deliver it, so it cannot race the
storage's invalidations.
"""

from DateTime import DateTime
from datetime import datetime
from datetime import UTC
from plone.uuid.interfaces import IUUID
from typing import Any

import re


VERSION = 1

_RESOLVEUID = re.compile(
    r"""(?P<prefix>(?:src|href)=["'])(?:\.\./)*resolveuid/(?P<uid>[0-9a-f]{32})"""
)


def iso_utc(value: datetime | DateTime) -> str:
    """Format a timestamp as ISO 8601 in UTC.

    Every producer uses this, so clients can compare two values as strings.
    A naive ``datetime`` is taken to be in UTC already.

    :param value: A Python ``datetime`` or a Zope ``DateTime``.
    :returns: The timestamp, e.g. ``2026-10-27T14:02:11+00:00``.
    """
    if isinstance(value, DateTime):
        value = value.asdatetime()
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def site_relative_links(html: str, resolve: Any, portal_url: str = "") -> str:
    """Rewrite links into the site as paths from the site root.

    The same message reaches every reader of the story, whatever host or
    rewrite they came through, so the body cannot carry a URL built for the
    request that saved it. Two forms are rewritten: ``resolveuid/<uid>``, as
    stored, and ``<portal_url>/...``, as Plone's output filters render it.

    :param html: Body HTML.
    :param resolve: Callable mapping a UID to a site-relative path, or
        ``None`` when the UID is unknown.
    :param portal_url: The site's URL in the request that built the message.
    :returns: The HTML with every resolvable link rewritten.
    """

    def replace(match: re.Match) -> str:
        path = resolve(match["uid"])
        if path is None:
            return match[0]
        return f"{match['prefix']}{path}"

    html = _RESOLVEUID.sub(replace, html)
    if portal_url:
        absolute = re.compile(
            r"""(?P<prefix>(?:src|href)=["'])"""
            + re.escape(portal_url.rstrip("/"))
            + r"""(?P<path>/[^"']*)?(?=["'])"""
        )
        html = absolute.sub(lambda m: f"{m['prefix']}{m['path'] or '/'}", html)
    return html


def _resolver(portal: Any) -> Any:
    from plone.app.uuid.utils import uuidToPhysicalPath

    portal_path = "/".join(portal.getPhysicalPath())

    def resolve(uid: str) -> str | None:
        path = uuidToPhysicalPath(uid)
        if not path or not path.startswith(portal_path):
            return None
        return path[len(portal_path) :] or "/"

    return resolve


def serialize(update: Any, story: Any) -> dict:
    """Build the message for an update.

    :param update: A ``BreakingNewsUpdate``.
    :param story: The ``BreakingNews`` that holds it.
    :returns: A JSON-serializable dict.
    """
    from plone import api

    body = update.body.output if update.body else ""
    if body:
        portal = api.portal.get()
        body = site_relative_links(body, _resolver(portal), portal.absolute_url())
    return {
        "v": VERSION,
        "kind": "update",
        "story": IUUID(story),
        "uid": IUUID(update),
        "datetime": iso_utc(update.datetime),
        "created": iso_utc(update.created()),
        "title": update.title or "",
        "body": body,
    }
