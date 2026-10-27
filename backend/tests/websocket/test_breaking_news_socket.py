from . import POLICY_VIOLATION
from . import UPDATES
from asgidemo.live import websocket as websocket_module
from plone import api
from starlette.websockets import WebSocketDisconnect

import json
import pytest


class TestRefused:
    """Readers who may not see the story never get an open socket."""

    def test_private_story_anonymous(self, client, private_story, socket_path):
        """A private story is refused with 1008, before the socket opens."""
        assert api.content.get_state(private_story) == "private"
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(socket_path(private_story.UID())),
        ):
            pass  # pragma: no cover
        assert exc.value.code == POLICY_VIOLATION

    def test_published_story_in_private_section(
        self, client, portal, hidden_story, socket_path
    ):
        """A story the catalog shows, behind a section the reader cannot enter."""
        section = portal["newsroom"]
        assert api.content.get_state(section) == "private"
        assert api.content.get_state(hidden_story) == "published"
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(socket_path(hidden_story.UID())),
        ):
            pass  # pragma: no cover
        assert exc.value.code == POLICY_VIOLATION

    def test_unknown_story(self, client, socket_path):
        """A UID that names no story looks exactly like a private one."""
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(socket_path("f" * 32)),
        ):
            pass  # pragma: no cover
        assert exc.value.code == POLICY_VIOLATION

    def test_not_a_story(self, client, portal, socket_path):
        """The UID of other content is refused too."""
        document = portal["brazil-2026"]["polls-open"]
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(socket_path(document.UID())),
        ):
            pass  # pragma: no cover
        assert exc.value.code == POLICY_VIOLATION

    @pytest.mark.parametrize("uid", ["not-a-uid", "0" * 31, "Z" * 32])
    def test_malformed_uid(self, client, uid, socket_path):
        """A malformed UID is refused without reaching Plone."""
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(socket_path(uid)),
        ):
            pass  # pragma: no cover
        assert exc.value.code == POLICY_VIOLATION


class TestAccepted:
    def test_private_story_manager(
        self, client, private_story, owner_headers, socket_path
    ):
        """Someone who may view the private story is let in."""
        path = socket_path(private_story.UID())
        with client.websocket_connect(path, headers=owner_headers) as socket:
            socket.close()

    def test_live_message(self, client, app, story, socket_path):
        """A message the hub receives reaches the connected reader."""
        message = {"v": 1, "kind": "update", "story": story.UID(), "uid": "u1"}
        with client.websocket_connect(socket_path(story.UID())) as socket:
            # The socket is accepted, so it has joined the hub.
            hub = app.state.breaking_news
            assert hub.counts() == {story.UID(): 1}
            hub.deliver(story.UID(), json.dumps(message))
            assert socket.receive_json() == message

    def test_leaves_hub_on_disconnect(self, client, app, story, socket_path):
        """A closed socket is removed from the hub."""
        with client.websocket_connect(socket_path(story.UID())) as socket:
            socket.close()
        assert app.state.breaking_news.counts() == {}


class TestCatchUp:
    def test_no_cursor_no_backlog(self, client, app, story, socket_path):
        """Without ``since``, the reader rendered everything: nothing is replayed."""
        marker = {"v": 1, "kind": "presence", "story": story.UID(), "readers": 1}
        with client.websocket_connect(socket_path(story.UID())) as socket:
            app.state.breaking_news.deliver(story.UID(), json.dumps(marker))
            assert socket.receive_json() == marker

    def test_backlog_since_cursor(self, client, story, socket_path):
        """Updates created since the cursor are replayed, oldest first."""
        since = "2000-01-01T00:00:00+00:00"
        with client.websocket_connect(socket_path(story.UID(), since)) as socket:
            received = [socket.receive_json() for _ in UPDATES]
        assert [m["kind"] for m in received] == ["update"] * len(UPDATES)
        assert [m["title"] for m in received] == [u["title"] for u in UPDATES]

    def test_too_far_behind(self, client, story, socket_path, monkeypatch):
        """A reader too far behind is told to reload instead."""
        monkeypatch.setattr(websocket_module, "CATCH_UP_LIMIT", 1)
        since = "2000-01-01T00:00:00+00:00"
        with client.websocket_connect(socket_path(story.UID(), since)) as socket:
            assert socket.receive_json() == {
                "v": 1,
                "kind": "reset",
                "story": story.UID(),
            }

    def test_bad_cursor_is_ignored(self, client, app, story, socket_path):
        """An unparsable cursor means no backlog, not an error."""
        marker = {"v": 1, "kind": "presence", "story": story.UID(), "readers": 1}
        with client.websocket_connect(socket_path(story.UID(), "yesterday-ish")) as s:
            app.state.breaking_news.deliver(story.UID(), json.dumps(marker))
            assert s.receive_json() == marker
