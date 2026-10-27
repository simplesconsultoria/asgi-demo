from . import STORY
from . import UPDATE
from collections.abc import Generator
from plone import api
from plone.app.textfield.value import RichTextValue
from Products.CMFPlone.Portal import PloneSite

import pytest


@pytest.fixture(scope="class")
def portal(portal_class) -> Generator[PloneSite]:
    """Yield the class-scoped Plone site."""
    yield portal_class


@pytest.fixture
def story(portal):
    """The story the ``portal`` marker created."""
    return portal[STORY["id"]]


@pytest.fixture
def add_update(story):
    """Return a helper that adds an update to the story, and removes it after.

    :param story: The story.
    :returns: Callable taking the update's id, title and body HTML.
    """
    created = []

    def func(id_: str = UPDATE["id"], title: str = UPDATE["title"], body: str = ""):
        update = api.content.create(
            container=story,
            type=UPDATE["type"],
            id=id_,
            title=title,
            body=RichTextValue(body, "text/html", "text/html") if body else None,
        )
        created.append(update)
        return update

    yield func
    for update in created:
        if update.getId() in story:
            api.content.delete(obj=update)
