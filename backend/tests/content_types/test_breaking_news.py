from . import STORY
from asgidemo.content.breaking_news import IBreakingNews
from plone.dexterity.fti import DexterityFTI
from plone.folder.interfaces import IExplicitOrdering

import pytest


PORTAL_TYPE = "BreakingNews"

BEHAVIORS = (
    "plone.dublincore",
    "plone.namefromtitle",
    "plone.shortname",
    "plone.excludefromnavigation",
    "plone.leadimage",
    "plone.versioning",
)


class TestBreakingNewsFTI:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, get_fti) -> None:
        """Bind the FTI of the type under test to the instance."""
        self.fti: DexterityFTI = get_fti(PORTAL_TYPE)

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("title", "Breaking News"),
            ("klass", "asgidemo.content.breaking_news.BreakingNews"),
            ("schema", "asgidemo.content.breaking_news.IBreakingNews"),
            ("add_permission", "asgidemo.AddBreakingNews"),
            ("global_allow", True),
            ("filter_content_types", True),
            ("allowed_content_types", ("BreakingNewsUpdate",)),
        ],
    )
    def test_fti(self, attr: str, expected):
        """Test FTI values."""
        assert isinstance(self.fti, DexterityFTI)
        assert getattr(self.fti, attr) == expected

    def test_behaviors_count(self):
        """No behavior is enabled beyond the expected ones."""
        assert len(self.fti.behaviors) == len(BEHAVIORS)

    @pytest.mark.parametrize("idx,behavior", list(enumerate(BEHAVIORS)))
    def test_behaviors(self, idx: int, behavior: str):
        """Test behaviors are present and in correct order."""
        assert self.fti.behaviors[idx] == behavior


@pytest.mark.portal(content=[STORY])
class TestBreakingNews:
    def test_provides_interface(self, story):
        """The story provides its schema interface."""
        assert IBreakingNews.providedBy(story)

    def test_live_by_default(self, story):
        """A new story is live."""
        assert story.live is True

    def test_unordered(self, story):
        """The container keeps no ordering list."""
        assert story.getOrdering().__class__.__name__ == "UnorderedOrdering"
        assert not IExplicitOrdering.providedBy(story.getOrdering())

    def test_versionable(self, versionable_content_types):
        """The type is registered in portal_repository."""
        assert PORTAL_TYPE in versionable_content_types
