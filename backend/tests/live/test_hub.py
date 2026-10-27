from asgidemo.live import hub as hub_module
from asgidemo.live import sql
from asgidemo.live.hub import backoff
from asgidemo.live.hub import Closed
from asgidemo.live.hub import Hub
from asgidemo.live.hub import PostgresBroker
from asgidemo.live.hub import SERVICE_RESTART
from asgidemo.live.hub import Subscriber
from asgidemo.live.hub import TRY_AGAIN_LATER

import asyncio
import json
import pytest


STORY = "0" * 32
OTHER = "1" * 32


def run(coro):
    # Bounded: a scenario that waits forever is a failure, not a hang.
    return asyncio.run(asyncio.wait_for(coro, timeout=5))


class TestSubscriber:
    def test_next_returns_in_order(self):
        """Messages come out in the order they went in."""

        async def scenario():
            subscriber = Subscriber(STORY)
            subscriber.deliver("a")
            subscriber.deliver("b")
            return [await subscriber.next(), await subscriber.next()]

        assert run(scenario()) == ["a", "b"]

    def test_close_jumps_the_queue(self):
        """A close is seen before anything still queued."""

        async def scenario():
            subscriber = Subscriber(STORY)
            subscriber.deliver("a")
            subscriber.close(SERVICE_RESTART)
            await subscriber.next()

        with pytest.raises(Closed) as exc:
            run(scenario())
        assert exc.value.code == SERVICE_RESTART

    def test_slow_reader_is_closed(self):
        """A reader that falls a full queue behind is closed with 1013."""

        async def scenario():
            subscriber = Subscriber(STORY, size=2)
            for data in ("a", "b", "c"):
                subscriber.deliver(data)
            await subscriber.next()

        with pytest.raises(Closed) as exc:
            run(scenario())
        assert exc.value.code == TRY_AGAIN_LATER

    def test_nothing_after_close(self):
        """A closed subscriber ignores further messages and closes."""

        async def scenario():
            subscriber = Subscriber(STORY)
            subscriber.close(SERVICE_RESTART)
            subscriber.deliver("late")
            subscriber.close(TRY_AGAIN_LATER)
            await subscriber.next()

        with pytest.raises(Closed) as exc:
            run(scenario())
        assert exc.value.code == SERVICE_RESTART


class TestHub:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.hub = Hub("backend-1")

    def test_deliver_reaches_only_the_story(self):
        """A message reaches the readers of its story and nobody else."""

        async def scenario():
            mine = self.hub.join(STORY)
            other = self.hub.join(OTHER)
            assert self.hub.deliver(STORY, "update") == 1
            assert other._queue.empty()
            return await mine.next()

        assert run(scenario()) == "update"

    def test_leave(self):
        """A story with no readers left is forgotten."""

        async def scenario():
            subscriber = self.hub.join(STORY)
            self.hub.leave(subscriber)
            return self.hub.local, self.hub.deliver(STORY, "update")

        assert run(scenario()) == ({}, 0)

    def test_counts(self):
        """Counts are per story."""

        async def scenario():
            self.hub.join(STORY)
            self.hub.join(STORY)
            self.hub.join(OTHER)
            return self.hub.counts()

        assert run(scenario()) == {STORY: 2, OTHER: 1}

    def test_close_all(self):
        """Every local reader is told to reconnect."""

        async def scenario():
            subscribers = [self.hub.join(STORY), self.hub.join(OTHER)]
            self.hub.close_all(SERVICE_RESTART)
            codes = []
            for subscriber in subscribers:
                try:
                    await subscriber.next()
                except Closed as exc:
                    codes.append(exc.code)
            return codes

        assert run(scenario()) == [SERVICE_RESTART, SERVICE_RESTART]


class TestBackoff:
    @pytest.mark.parametrize("attempt", list(range(12)))
    def test_bounded(self, attempt):
        """Delays are jittered between zero and a cap."""
        delay = backoff(attempt, cap=30.0)
        assert 0 <= delay <= min(30.0, 0.5 * 2**attempt)


class FakeCursor:
    def __init__(self, rows, description=True):
        self.rows = rows
        self.description = description or None

    async def fetchall(self):
        return self.rows


class FakeConnection:
    """Answers the broker's queries from canned data."""

    def __init__(self, outbox=None, totals=None):
        self.outbox = outbox or {}
        self.totals = totals or []
        self.closed = False
        self.executed = []

    async def execute(self, query, params=None):
        self.executed.append((query, params))
        if query == sql.SELECT_MESSAGE:
            row = self.outbox.get(params["id"])
            return FakeCursor([(row,)] if row else [])
        if query == sql.TOTAL_PRESENCE:
            return FakeCursor(self.totals)
        return FakeCursor([], description=False)

    async def close(self):
        self.closed = True


class TestPostgresBroker:
    def make(self, connection, hub=None):
        async def connect(dsn, autocommit):
            assert autocommit is True
            return connection

        return PostgresBroker("dbname=test", hub or Hub("backend-1"), connect=connect)

    def test_notification_delivers_the_outbox_row(self):
        """A notification's id is read from the outbox and handed to readers."""
        message = {"v": 1, "kind": "update", "story": STORY, "uid": "u1"}
        broker = self.make(FakeConnection(outbox={7: message}))

        async def scenario():
            subscriber = broker.hub.join(STORY)
            await broker.handle_notification("7")
            return json.loads(await subscriber.next())

        assert run(scenario()) == message

    @pytest.mark.parametrize("payload", ["not-a-number", "99"])
    def test_bad_or_missing_rows_are_ignored(self, payload):
        """A malformed payload or a pruned row delivers nothing."""
        broker = self.make(FakeConnection())

        async def scenario():
            subscriber = broker.hub.join(STORY)
            await broker.handle_notification(payload)
            return subscriber._queue.empty()

        assert run(scenario()) is True

    def test_presence_reports_and_pushes_totals(self):
        """Local counts go to PostgreSQL; the totals come back to readers."""
        connection = FakeConnection(totals=[(STORY, 42)])
        broker = self.make(connection)

        async def scenario():
            subscriber = broker.hub.join(STORY)
            await broker.report_presence()
            return json.loads(await subscriber.next())

        assert run(scenario()) == {
            "v": 1,
            "kind": "presence",
            "story": STORY,
            "readers": 42,
        }
        queries = [query for query, _ in connection.executed]
        assert queries == [
            sql.REPORT_PRESENCE,
            sql.FORGET_PRESENCE,
            sql.TOTAL_PRESENCE,
        ]
        assert connection.executed[0][1] == {
            "backend": "backend-1",
            "story": STORY,
            "readers": 1,
        }

    def test_presence_without_readers(self):
        """With no local readers, this backend only withdraws its reports."""
        connection = FakeConnection()
        broker = self.make(connection)
        run(broker.report_presence())
        assert [query for query, _ in connection.executed] == [sql.FORGET_PRESENCE]

    def test_resubscribe_closes_local_sockets(self, monkeypatch):
        """After a lost LISTEN connection, readers are told to reconnect."""

        class ListenConnection:
            def __init__(self, fail):
                self.fail = fail

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def execute(self, query, params=None):
                assert query == sql.LISTEN

            async def notifies(self):
                if self.fail:
                    raise ConnectionError("server closed the connection")
                await asyncio.Event().wait()
                yield  # pragma: no cover

        connections = iter([ListenConnection(fail=True), ListenConnection(fail=False)])

        async def connect(dsn, autocommit):
            return next(connections)

        monkeypatch.setattr(hub_module, "backoff", lambda attempt: 0)
        broker = PostgresBroker("dbname=test", Hub("backend-1"), connect=connect)

        async def scenario():
            subscriber = broker.hub.join(STORY)
            task = asyncio.create_task(broker.listen_forever())
            try:
                await subscriber.next()
            except Closed as exc:
                return exc.code
            finally:
                task.cancel()

        assert run(scenario()) == SERVICE_RESTART
