"""Serve the site under uvicorn with ploneasgi.

Run with ``python -m asgidemo.server``. Settings come from the environment
(``PLONE_ZOPE_CONF``, ``PLONE_CONCURRENCY``, ...; see ploneasgi's settings),
and the Breaking News hub listens on ``BREAKING_NEWS_DSN``, or on the ZODB's
``ZODB_PGJSONB_DSN``.
"""

from asgidemo.live.lifespan import breaking_news_lifespan
from ploneasgi import create_app
from ploneasgi import load_env
from ploneasgi import serve
from ploneasgi import Settings
from ploneasgi.zcml import routes_from_registry
from ploneasgi.zopeapp import build_wsgi_app
from ploneasgi.zopeapp import check_concurrency_contract
from starlette.applications import Starlette


def make_app(settings: Settings | None = None) -> Starlette:
    """Start Zope and build the ASGI application.

    :param settings: ploneasgi settings; read from the environment when omitted.
    :returns: The application, with the ZCML routes and the hub's lifespan.
    """
    settings = settings or Settings.from_env()
    # Starting Zope executes the ZCML, which registers the routes collected below.
    wsgi_app = build_wsgi_app(settings)
    check_concurrency_contract(settings)
    return create_app(
        settings,
        routes=routes_from_registry(prefix=settings.route_prefix),
        lifespans=[breaking_news_lifespan],
        wsgi_app=wsgi_app,
    )


def main() -> None:
    """Load ``.env``, build the application and serve it."""
    load_env()
    settings = Settings.from_env()
    serve(make_app(settings), settings)


if __name__ == "__main__":
    main()
