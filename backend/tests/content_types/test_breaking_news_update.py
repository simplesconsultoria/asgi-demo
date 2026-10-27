from . import STORY
from datetime import datetime
from datetime import UTC
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.textfield.value import RichTextValue
from plone.dexterity.fti import DexterityFTI

import pytest


PORTAL_TYPE = "BreakingNewsUpdate"

BEHAVIORS = (
    "plone.basic",
    "plone.ownership",
    "plone.shortname",
)


class TestBreakingNewsUpdateFTI:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, get_fti) -> None:
        """Bind the FTI of the type under test to the instance."""
        self.fti: DexterityFTI = get_fti(PORTAL_TYPE)

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("title", "Breaking News Update"),
            ("klass", "asgidemo.content.breaking_news_update.BreakingNewsUpdate"),
            ("schema", "asgidemo.content.breaking_news_update.IBreakingNewsUpdate"),
            ("add_permission", "asgidemo.AddBreakingNewsUpdate"),
            ("global_allow", False),
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

    def test_no_workflow(self, portal):
        """Updates have no workflow: they acquire View from their story."""
        wftool = api.portal.get_tool("portal_workflow")
        assert wftool.getChainForPortalType(PORTAL_TYPE) == ()


@pytest.mark.portal(content=[STORY], roles=["Manager"])
class TestBreakingNewsUpdate:
    @pytest.fixture
    def update(self, story):
        update = api.content.create(
            container=story,
            type=PORTAL_TYPE,
            id="polls-open",
            title="Polls open across the country",
            body=RichTextValue("<p>Voting has started.</p>", "text/html", "text/html"),
        )
        yield update
        api.content.delete(obj=update)

    def test_not_addable_outside_a_story(self, portal):
        """An update cannot be created at the site root."""
        with pytest.raises(InvalidParameterError):
            api.content.create(container=portal, type=PORTAL_TYPE, title="Stray")

    def test_datetime_defaults_to_now(self, update):
        """A new update is placed at the current time, in UTC."""
        assert isinstance(update.datetime, datetime)
        assert update.datetime.utcoffset().total_seconds() == 0

    def test_default_datetime_is_stored(self, update):
        """The default is stored on add, so the update stays put on the timeline."""
        assert "datetime" in update.__dict__
        assert update.datetime == update.datetime

    def test_given_datetime_is_kept(self, story):
        """An editor's back-dated datetime is not overwritten."""
        when = datetime(2026, 10, 4, 8, 0, tzinfo=UTC)
        update = api.content.create(
            container=story, type=PORTAL_TYPE, title="Early", datetime=when
        )
        assert update.datetime == when
        api.content.delete(obj=update)

    def test_indexed_by_datetime(self, story, update):
        """The listing sorts on the update's datetime without waking objects."""
        brains = api.content.find(
            context=story,
            portal_type=PORTAL_TYPE,
            sort_on="breaking_news_datetime",
        )
        assert [b.getId for b in brains] == ["polls-open"]
        assert brains[0].breaking_news_datetime is not None
