from asgidemo.live.messages import serialize
from asgidemo.setuphandlers.breaking_news import create_breaking_news
from plone import api

import re


IMG = re.compile(r"<img\b")


class TestImages:
    def test_folder(self, portal):
        """The images live in a published /images folder."""
        assert api.content.get_state(portal["images"]) == "published"

    def test_ten_distinct_images(self, portal):
        """Ten images, each with its own picture."""
        images = portal["images"].objectValues()
        assert len(images) == 10
        assert {image.portal_type for image in images} == {"Image"}
        assert len({image.image.data for image in images}) == 10


class TestStory:
    def test_story(self, story):
        """The example story has the agreed id and title, and is public."""
        assert story.portal_type == "BreakingNews"
        assert story.title == "Brazil Elections 2026"
        assert api.content.get_state(story) == "published"
        assert story.live is True

    def test_at_least_forty_updates(self, updates):
        """The story is long enough to scroll and to load older updates."""
        assert len(updates) >= 40
        assert {update.portal_type for update in updates} == {"BreakingNewsUpdate"}

    def test_at_most_one_image_per_update(self, updates):
        """No update carries more than one image."""
        counts = [len(IMG.findall(update.body.raw)) for update in updates]
        assert max(counts) == 1

    def test_not_every_update_has_an_image(self, updates):
        """Some updates are text only."""
        counts = [len(IMG.findall(update.body.raw)) for update in updates]
        assert 0 < sum(counts) < len(updates)

    def test_timeline_is_in_order(self, updates):
        """Updates are spread through election day, Brasília time."""
        first, last = updates[0].datetime, updates[-1].datetime
        assert first.isoformat() == "2026-10-04T10:45:00+00:00"
        assert last.isoformat() == "2026-10-05T00:30:00+00:00"

    def test_images_reach_readers_as_site_paths(self, story, updates):
        """Images are linked by UID, and sent to readers as site paths."""
        with_image = next(u for u in updates if IMG.search(u.body.raw))
        assert "resolveuid/" in with_image.body.raw
        body = serialize(with_image, story)["body"]
        assert re.search(r'src="/images/[a-z-]+/@@images/image[^"]*"', body)

    def test_idempotent(self, portal, story):
        """Running the creator again adds nothing."""
        before = len(story)
        with api.env.adopt_roles(["Manager"]):
            create_breaking_news(portal)
        assert len(story) == before
        assert len(portal["images"]) == 10
