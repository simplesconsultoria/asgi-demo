from . import IMAGE_FOLDER
from . import PNG
from . import STORY
from asgidemo.live.messages import iso_utc
from asgidemo.live.messages import serialize
from asgidemo.live.messages import site_relative_links
from DateTime import DateTime
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import UTC
from plone import api
from plone.namedfile.file import NamedBlobImage

import pytest


class TestIsoUtc:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (
                datetime(2026, 10, 4, 17, 0, 0, 123456, tzinfo=UTC),
                "2026-10-04T17:00:00+00:00",
            ),
            (
                datetime(2026, 10, 4, 14, 0, tzinfo=timezone(timedelta(hours=-3))),
                "2026-10-04T17:00:00+00:00",
            ),
            (datetime(2026, 10, 4, 17, 0), "2026-10-04T17:00:00+00:00"),
            (DateTime("2026/10/04 14:00:00 GMT-3"), "2026-10-04T17:00:00+00:00"),
        ],
    )
    def test_iso_utc(self, value, expected):
        """Every producer formats timestamps the same way, in UTC."""
        assert iso_utc(value) == expected


class TestSiteRelativeLinks:
    UID = "0123456789abcdef0123456789abcdef"

    def resolve(self, uid):
        return "/images/ballot-box" if uid == self.UID else None

    @pytest.mark.parametrize(
        "html,expected",
        [
            (
                f'<img src="resolveuid/{UID}/@@images/image/large">',
                '<img src="/images/ballot-box/@@images/image/large">',
            ),
            (
                f"<a href='../../resolveuid/{UID}'>x</a>",
                "<a href='/images/ballot-box'>x</a>",
            ),
            (
                '<img src="resolveuid/ffffffffffffffffffffffffffffffff">',
                '<img src="resolveuid/ffffffffffffffffffffffffffffffff">',
            ),
            ("<p>resolveuid/ in prose</p>", "<p>resolveuid/ in prose</p>"),
        ],
    )
    def test_rewrite(self, html, expected):
        """Known UIDs become site-relative paths; anything else is left alone."""
        assert site_relative_links(html, self.resolve) == expected

    @pytest.mark.parametrize(
        "html,expected",
        [
            (
                '<img src="http://localhost:8080/Plone/images/x/@@images/image/large">',
                '<img src="/images/x/@@images/image/large">',
            ),
            ('<a href="http://localhost:8080/Plone">home</a>', '<a href="/">home</a>'),
            (
                '<a href="http://localhost:8080/Plone2/page">other site</a>',
                '<a href="http://localhost:8080/Plone2/page">other site</a>',
            ),
            (
                '<a href="https://example.org/elsewhere">out</a>',
                '<a href="https://example.org/elsewhere">out</a>',
            ),
        ],
    )
    def test_rewrite_portal_url(self, html, expected):
        """Links rendered against the request's site URL become site paths."""
        url = "http://localhost:8080/Plone"
        assert site_relative_links(html, self.resolve, url) == expected


@pytest.mark.portal(content=[STORY, IMAGE_FOLDER], roles=["Manager"])
class TestSerialize:
    @pytest.fixture
    def image(self, portal):
        image = api.content.create(
            container=portal[IMAGE_FOLDER["id"]],
            type="Image",
            id="ballot-box",
            title="Ballot box",
            image=NamedBlobImage(data=PNG, filename="ballot-box.png"),
        )
        yield image
        api.content.delete(obj=image, check_linkintegrity=False)

    def test_shape(self, story, add_update):
        """The message carries the whole update."""
        update = add_update(body="<p>Voting has started.</p>")
        message = serialize(update, story)
        assert set(message) == {
            "v",
            "kind",
            "story",
            "uid",
            "datetime",
            "created",
            "title",
            "body",
        }
        assert message["v"] == 1
        assert message["kind"] == "update"
        assert message["story"] == story.UID()
        assert message["uid"] == update.UID()
        assert message["title"] == "Polls open across the country"
        assert "Voting has started." in message["body"]
        assert message["created"].endswith("+00:00")
        assert message["datetime"].endswith("+00:00")

    def test_empty_body(self, story, add_update):
        """An update without a body sends an empty string."""
        assert serialize(add_update(), story)["body"] == ""

    def test_image_link_is_site_relative(self, story, add_update, image):
        """An image referenced by UID is sent as a path from the site root."""
        body = f'<p><img src="resolveuid/{image.UID()}/@@images/image/large"></p>'
        message = serialize(add_update(body=body), story)
        assert 'src="/images/ballot-box/@@images/image/large"' in message["body"]
