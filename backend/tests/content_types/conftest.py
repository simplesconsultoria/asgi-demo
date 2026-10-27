from . import STORY
from collections.abc import Generator
from plone import api
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
def versionable_content_types(portal) -> list[str]:
    """The portal types versioning is enabled for.

    :param portal: Plone site.
    :returns: Portal type ids registered in ``portal_repository``.
    """
    return api.portal.get_tool("portal_repository").getVersionableContentTypes()
