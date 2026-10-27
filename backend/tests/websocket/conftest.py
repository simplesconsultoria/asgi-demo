from . import HIDDEN_STORY
from . import PRIVATE_SECTION
from . import PRIVATE_STORY
from . import STORY
from . import UPDATES
from asgidemo.live.hub import Hub
from collections.abc import Generator
from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from ploneasgi import context
from ploneasgi import create_app
from ploneasgi import Settings
from ploneasgi.zcml import routes_from_registry
from Products.CMFPlone.Portal import PloneSite
from starlette.testclient import TestClient
from urllib.parse import quote

import base64
import pytest
import transaction


@pytest.fixture(scope="class")
def portal(functional_portal_class) -> Generator[PloneSite]:
    """Yield the class-scoped functional site, with the stories committed.

    A native route reaches Plone on a second ZODB connection, which sees only
    what has been committed.
    """
    portal = functional_portal_class
    with api.env.adopt_roles(["Manager"]):
        story = api.content.create(container=portal, **STORY)
        api.content.transition(obj=story, transition="publish")
        for update in UPDATES:
            api.content.create(container=story, type="BreakingNewsUpdate", **update)
        api.content.create(container=portal, **PRIVATE_STORY)
        section = api.content.create(container=portal, **PRIVATE_SECTION)
        hidden = api.content.create(container=section, **HIDDEN_STORY)
        api.content.transition(obj=hidden, transition="publish")
    transaction.commit()
    yield portal


@pytest.fixture
def story(portal):
    return portal[STORY["id"]]


@pytest.fixture
def private_story(portal):
    return portal[PRIVATE_STORY["id"]]


@pytest.fixture
def hidden_story(portal):
    return portal[PRIVATE_SECTION["id"]][HIDDEN_STORY["id"]]


@pytest.fixture
def app(portal, monkeypatch):
    """The ASGI application, with the routes ZCML registered.

    Its lifespan never runs: ploneasgi's own closes ``Zope2.DB`` on exit,
    which would close the layer's database under the next test. The hub is
    attached by hand, local-only, as the Breaking News lifespan would without
    a PostgreSQL to listen on.
    """
    monkeypatch.setattr(context, "default_db", lambda: portal._p_jar.db())
    settings = Settings(site_id=portal.getId())

    def no_zope(environ, start_response):  # pragma: no cover - never reached
        start_response("404 Not Found", [])
        return [b""]

    app = create_app(
        settings,
        routes=routes_from_registry(prefix=settings.route_prefix),
        wsgi_app=no_zope,
    )
    app.state.breaking_news = Hub("test-backend")
    return app


@pytest.fixture
def client(app) -> Generator[TestClient]:
    """A test client; used without ``with``, so no lifespan runs."""
    yield TestClient(app)


@pytest.fixture
def owner_headers() -> dict:
    """Basic credentials of the site owner, a Manager."""
    token = base64.b64encode(f"{SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}".encode())
    return {"Authorization": f"Basic {token.decode()}"}


@pytest.fixture
def socket_path():
    """Return a helper building the websocket path for a story.

    :returns: Callable taking a UID and an optional ``since`` cursor.
    """

    def func(uid: str, since: str | None = None) -> str:
        path = f"/++asgi++/breaking-news/{uid}"
        # Encoded, as the browser's encodeURIComponent does: a bare "+" in
        # "+00:00" would arrive as a space.
        return f"{path}?since={quote(since, safe='')}" if since else path

    return func
