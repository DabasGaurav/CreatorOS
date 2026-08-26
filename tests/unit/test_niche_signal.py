from datetime import UTC, datetime

from click.testing import CliRunner

from creatoros.niche import cli as niche_cli
from creatoros.niche.repository import add_niche_signal, list_niche_signal


class FakeSession:
    """Minimal in-memory stand-in for a SQLAlchemy Session, enough to exercise the
    repository layer's contract without a live Postgres connection."""

    def __init__(self):
        self.rows = []
        self._next_id = 1

    def add(self, row):
        row.id = self._next_id
        self._next_id += 1
        self.rows.append(row)

    def commit(self):
        pass

    def refresh(self, row):
        pass

    def query(self, model):
        return FakeQuery(self.rows)


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, condition):
        # condition is a SQLAlchemy BinaryExpression like NicheSignal.niche == "x";
        # extract the compared value via its right-hand side for this simple fake.
        niche_value = condition.right.value
        return FakeQuery([r for r in self._rows if r.niche == niche_value])

    def order_by(self, *_args):
        return self

    def all(self):
        return sorted(self._rows, key=lambda r: r.observed_at, reverse=True)


def test_add_niche_signal_inserts_and_commits():
    session = FakeSession()
    row = add_niche_signal(
        session,
        niche="AI/startups",
        account_handle="@example",
        observed_topic="AI coding agents",
        added_by="founder",
    )
    assert row in session.rows
    assert row.niche == "AI/startups"
    assert row.observed_at is not None


def test_list_niche_signal_filters_by_niche():
    session = FakeSession()
    add_niche_signal(
        session,
        niche="AI/startups",
        account_handle="@a",
        observed_topic="topic a",
        added_by="founder",
    )
    add_niche_signal(
        session,
        niche="fitness",
        account_handle="@b",
        observed_topic="topic b",
        added_by="founder",
    )
    results = list_niche_signal(session, niche="AI/startups")
    assert len(results) == 1
    assert results[0].account_handle == "@a"


def test_add_niche_signal_accepts_explicit_observed_at():
    session = FakeSession()
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    row = add_niche_signal(
        session,
        niche="AI/startups",
        account_handle="@a",
        observed_topic="topic a",
        added_by="founder",
        observed_at=ts,
    )
    assert row.observed_at == ts


def test_cli_add_command_invokes_repository(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(niche_cli, "get_session", lambda: session)

    runner = CliRunner()
    result = runner.invoke(
        niche_cli.cli,
        [
            "add",
            "--niche",
            "AI/startups",
            "--account",
            "@example",
            "--topic",
            "AI coding agents",
            "--added-by",
            "founder",
        ],
    )
    assert result.exit_code == 0
    assert "Added niche_signal row" in result.output
    assert len(session.rows) == 1
