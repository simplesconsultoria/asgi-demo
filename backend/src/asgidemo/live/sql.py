"""SQL shared by the outbox writer and the hub.

Zope-free on purpose: the hub imports it on the event loop.
"""

CHANNEL = "breaking_news"

SCHEMA = """
CREATE TABLE IF NOT EXISTS breaking_news_outbox (
    id         bigserial   PRIMARY KEY,
    story      text        NOT NULL,
    payload    jsonb       NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS breaking_news_outbox_created_at
    ON breaking_news_outbox (created_at);

CREATE TABLE IF NOT EXISTS breaking_news_presence (
    backend_id text        NOT NULL,
    story      text        NOT NULL,
    readers    integer     NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (backend_id, story)
);
"""

# One statement per message: the row and its notification are written by the
# same transaction, so PostgreSQL delivers the NOTIFY only if the row commits.
INSERT_AND_NOTIFY = f"""
WITH row AS (
    INSERT INTO breaking_news_outbox (story, payload)
    VALUES (%(story)s, %(payload)s)
    RETURNING id
)
SELECT pg_notify('{CHANNEL}', id::text) FROM row
"""  # noqa: S608 - CHANNEL is a constant

LISTEN = f"LISTEN {CHANNEL}"

SELECT_MESSAGE = "SELECT payload FROM breaking_news_outbox WHERE id = %(id)s"

PRUNE_OUTBOX = """
DELETE FROM breaking_news_outbox
WHERE created_at < now() - make_interval(secs => %(keep)s)
"""

REPORT_PRESENCE = """
INSERT INTO breaking_news_presence (backend_id, story, readers, updated_at)
VALUES (%(backend)s, %(story)s, %(readers)s, now())
ON CONFLICT (backend_id, story)
DO UPDATE SET readers = EXCLUDED.readers, updated_at = EXCLUDED.updated_at
"""

FORGET_PRESENCE = """
DELETE FROM breaking_news_presence
WHERE backend_id = %(backend)s AND NOT (story = ANY(%(stories)s))
"""

TOTAL_PRESENCE = """
SELECT story, SUM(readers)::integer AS readers
FROM breaking_news_presence
WHERE story = ANY(%(stories)s)
  AND updated_at > now() - make_interval(secs => %(expiry)s)
GROUP BY story
"""

PRUNE_PRESENCE = """
DELETE FROM breaking_news_presence
WHERE updated_at < now() - make_interval(secs => %(keep)s)
"""
