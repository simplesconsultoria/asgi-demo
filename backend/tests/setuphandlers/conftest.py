from asgidemo.setuphandlers.breaking_news import create_breaking_news
from collections.abc import Generator
from plone import api
from Products.CMFPlone.Portal import PloneSite

import pytest


@pytest.fixture(scope="class")
def portal(portal_class) -> Generator[PloneSite]:
    """Yield the class-scoped Plone site, with the example story created."""
    with api.env.adopt_roles(["Manager"]):
        create_breaking_news(portal_class)
    yield portal_class


@pytest.fixture
def story(portal):
    return portal["brazil-2026"]


@pytest.fixture
def updates(story) -> list:
    """The story's updates, oldest first."""
    return sorted(story.objectValues(), key=lambda update: update.datetime)
