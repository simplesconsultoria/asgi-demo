from . import STORY
from asgidemo.live import outbox
from asgidemo.live import sql
from psycopg.types.json import Jsonb
from types import SimpleNamespace

import pytest
import transaction


class FakeCursor:
    """Records what the processor would run on the commit's PG transaction."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, dict]] = []

    def execute(self, query: str, params: dict) -> None:
        self.executed.append((query, params))


def run_before_commit_hooks(txn) -> None:
    for hook, args, kwargs in txn.getBeforeCommitHooks():
        hook(*args, **kwargs)


def messages_for(txn, obj) -> list[dict]:
    # The class-scoped integration layer never commits, so the transaction
    # still carries the hooks of earlier tests: look at this object only.
    return [m for m in outbox.pending(txn) if m["uid"] == obj.UID()]


class TestPending:
    @pytest.fixture(autouse=True)
    def _clean(self):
        transaction.abort()
        yield
        transaction.abort()

    def test_empty_by_default(self):
        """Nothing is queued on a fresh transaction."""
        assert outbox.pending() == []

    def test_reading_does_not_attach(self):
        """Asking for the queue does not attach one to the transaction."""
        txn = transaction.get()
        outbox.pending(txn)
        with pytest.raises(KeyError):
            txn.data(outbox._KEY)

    def test_enqueue(self):
        """Messages queue in order on the current transaction."""
        outbox.enqueue({"uid": "a"})
        outbox.enqueue({"uid": "b"})
        assert [m["uid"] for m in outbox.pending()] == ["a", "b"]

    def test_scoped_to_transaction(self):
        """A queued message does not survive into the next transaction."""
        outbox.enqueue({"uid": "a"})
        transaction.abort()
        assert outbox.pending() == []


class TestOutboxProcessor:
    @pytest.fixture(autouse=True)
    def _setup(self):
        transaction.abort()
        self.processor = outbox.OutboxProcessor()
        self.cursor = FakeCursor()
        yield
        transaction.abort()

    def test_owns_no_columns(self):
        """The processor leaves object_state alone."""
        assert self.processor.get_extra_columns() == []
        assert self.processor.process(1, "mod", "Class", {}) is None

    def test_schema(self):
        """The processor creates the outbox and presence tables."""
        schema = self.processor.get_schema_sql()
        assert "breaking_news_outbox" in schema
        assert "breaking_news_presence" in schema

    def test_finalize_without_messages_runs_nothing(self):
        """Every commit votes through finalize; most have nothing to write."""
        self.processor.finalize(self.cursor)
        assert self.cursor.executed == []

    def test_finalize_writes_and_notifies(self):
        """Each message is inserted and notified in the commit's transaction."""
        outbox.enqueue({"story": "s1", "uid": "a"})
        outbox.enqueue({"story": "s1", "uid": "b"})
        self.processor.finalize(self.cursor)
        assert len(self.cursor.executed) == 2
        query, params = self.cursor.executed[0]
        assert query == sql.INSERT_AND_NOTIFY
        assert "pg_notify" in query
        assert params["story"] == "s1"
        assert isinstance(params["payload"], Jsonb)
        assert params["payload"].obj == {"story": "s1", "uid": "a"}

    def test_finalize_twice_writes_once(self):
        """A second vote on the same transaction does not write again."""
        outbox.enqueue({"story": "s1", "uid": "a"})
        self.processor.finalize(self.cursor)
        self.processor.finalize(self.cursor)
        assert len(self.cursor.executed) == 1


class TestRegisterProcessor:
    def test_pgjsonb(self):
        """On PGJsonb the processor is registered on the main storage."""
        registered = []
        storage = SimpleNamespace(register_state_processor=registered.append)
        event = SimpleNamespace(database=SimpleNamespace(storage=storage))
        outbox.register_processor(event)
        assert len(registered) == 1
        assert isinstance(registered[0], outbox.OutboxProcessor)

    def test_other_storage(self):
        """Any other storage is left alone, with a warning."""
        event = SimpleNamespace(database=SimpleNamespace(storage=object()))
        outbox.register_processor(event)


@pytest.mark.portal(content=[STORY], roles=["Manager"])
class TestAnnounce:
    def test_message_built_at_commit(self, story, add_update):
        """Adding an update queues nothing until the transaction commits."""
        txn = transaction.get()
        update = add_update(body="<p>Polls open.</p>")
        assert messages_for(txn, update) == []
        run_before_commit_hooks(txn)
        queued = messages_for(txn, update)
        assert len(queued) == 1
        assert queued[0]["story"] == story.UID()

    def test_reads_final_state(self, add_update):
        """The message has fields set after the add event fired."""
        txn = transaction.get()
        update = add_update()
        update.title = "Polls open, turnout high"
        run_before_commit_hooks(txn)
        assert messages_for(txn, update)[0]["title"] == "Polls open, turnout high"

    def test_other_content_queues_nothing(self, portal):
        """Only updates are announced."""
        from plone import api

        txn = transaction.get()
        document = api.content.create(
            container=portal, type="Document", title="Unrelated"
        )
        run_before_commit_hooks(txn)
        assert messages_for(txn, document) == []
