"""Example content: a live story with dozens of updates and ten images.

``updates.json`` holds the story; ``images/`` holds the illustrations, drawn
by ``scripts/generate_example_images.py``. Running :func:`create_breaking_news`
twice changes nothing: existing content is left as it is.
"""

from asgidemo import logger
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import UTC
from pathlib import Path
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobImage
from typing import Any
from zope.component import getUtility

import json


DATA_FOLDER = Path(__file__).parent
IMAGES_FOLDER = DATA_FOLDER / "images"

IMAGES_CONTAINER = {"type": "Document", "id": "images", "title": "Images"}

#: Election day, in Brasília time.
ELECTION_DAY = date(2026, 10, 4)
BRASILIA = timezone(timedelta(hours=-3))


def load() -> dict:
    """:returns: The story, images and updates from ``updates.json``."""
    return json.loads((DATA_FOLDER / "updates.json").read_text())


def _publish(obj: Any) -> None:
    if api.content.get_state(obj, default=None) not in (None, "published"):
        api.content.transition(obj=obj, transition="publish")


def create_images(portal: Any, images: list[dict]) -> dict[str, Any]:
    """Create the ``/images`` folder and one Image per illustration.

    :param portal: The Plone site.
    :param images: Entries with ``id`` and ``title``.
    :returns: The Image objects by id.
    """
    container = portal.get(IMAGES_CONTAINER["id"])
    if container is None:
        container = api.content.create(container=portal, **IMAGES_CONTAINER)
    _publish(container)
    created = {}
    for entry in images:
        image = container.get(entry["id"])
        if image is None:
            path = IMAGES_FOLDER / f"{entry['id']}.jpg"
            image = api.content.create(
                container=container,
                type="Image",
                id=entry["id"],
                title=entry["title"],
                image=NamedBlobImage(data=path.read_bytes(), filename=path.name),
            )
        _publish(image)
        created[entry["id"]] = image
    return created


def update_body(body: str, image: Any | None, alt: str) -> RichTextValue:
    """The update's body, with its image first when it has one.

    The image is linked by UID, as an editor's link would be; the message sent
    to readers rewrites it to a path from the site root.

    :param body: Body HTML.
    :param image: The Image to show above the text, or ``None``.
    :param alt: Alternative text for the image.
    :returns: The rich text value.
    """
    if image is not None:
        img = (
            f'<p><img class="image-richtext" alt="{alt}" '
            f'src="resolveuid/{image.UID()}/@@images/image/large" /></p>'
        )
        body = img + body
    return RichTextValue(body, "text/html", "text/x-html-safe")


def create_breaking_news(portal: Any) -> Any:
    """Create the example story with its updates.

    :param portal: The Plone site.
    :returns: The story.
    """
    data = load()
    images = create_images(portal, data["images"])
    titles = {entry["id"]: entry["title"] for entry in data["images"]}
    info = data["story"]
    story = portal.get(info["id"])
    if story is None:
        lead = images[info["lead_image"]]
        story = api.content.create(
            container=portal,
            type="BreakingNews",
            id=info["id"],
            title=info["title"],
            description=info["description"],
            image=NamedBlobImage(data=lead.image.data, filename=lead.image.filename),
        )
    _publish(story)
    normalizer = getUtility(IIDNormalizer)
    for entry in data["updates"]:
        update_id = normalizer.normalize(entry["title"], max_length=60)
        if update_id in story:
            continue
        hour, minute = (int(part) for part in entry["time"].split(":"))
        image_id = entry.get("image")
        api.content.create(
            container=story,
            type="BreakingNewsUpdate",
            id=update_id,
            title=entry["title"],
            datetime=datetime
            .combine(ELECTION_DAY, datetime.min.time())
            .replace(hour=hour, minute=minute, tzinfo=BRASILIA)
            .astimezone(UTC),
            body=update_body(
                entry["body"], images.get(image_id), titles.get(image_id, "")
            ),
        )
    logger.info("Breaking News story %s has %d updates", story.getId(), len(story))
    return story
