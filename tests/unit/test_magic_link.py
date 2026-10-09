import uuid
from datetime import UTC, datetime, timedelta

from creatorsignal.auth import magic_link as ml
from creatorsignal.db.models import Creator, MagicLinkToken
from creatorsignal.db.models import Session as SessionModel


class FakeQuery:
    def __init__(self, rows, model):
        self._rows = rows
        self._model = model

    def filter(self, condition):
        col_name = condition.left.name
        value = condition.right.value
        matched = [r for r in self._rows if getattr(r, col_name, None) == value]
        return FakeQuery(matched, self._model)

    def one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self, creators=(), tokens=(), sessions=()):
        self.creators = list(creators)
        self.tokens = list(tokens)
        self.sessions = list(sessions)
        self.added = []

    def query(self, model):
        if model is Creator:
            return FakeQuery(self.creators, model)
        if model is MagicLinkToken:
            return FakeQuery(self.tokens, model)
        if model is SessionModel:
            return FakeQuery(self.sessions, model)
        raise AssertionError(f"unexpected model {model}")

    def add(self, row):
        self.added.append(row)
        if isinstance(row, MagicLinkToken):
            self.tokens.append(row)
        elif isinstance(row, SessionModel):
            self.sessions.append(row)

    def commit(self):
        pass

    def refresh(self, row):
        pass


def _creator(email="creator@example.com"):
    return Creator(
        id=uuid.uuid4(),
        instagram_user_id="ig-1",
        display_name="Test Creator",
        niche="tech",
        email=email,
        token="ciphertext",
        token_expires_at=datetime.now(UTC) + timedelta(days=60),
    )


def test_request_magic_link_returns_false_for_unknown_email(monkeypatch):
    sent = {"n": 0}
    monkeypatch.setattr(ml, "send_email", lambda **kwargs: sent.__setitem__("n", sent["n"] + 1))

    session = FakeSession()
    result = ml.request_magic_link(session, "nobody@example.com")

    assert result is False
    assert sent["n"] == 0


def test_request_magic_link_sends_email_for_known_creator(monkeypatch):
    captured = {}

    def fake_send_email(*, to, subject, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["html"] = html

    monkeypatch.setattr(ml, "send_email", fake_send_email)

    creator = _creator()
    session = FakeSession(creators=[creator])
    result = ml.request_magic_link(session, "creator@example.com")

    assert result is True
    assert captured["to"] == "creator@example.com"
    assert len(session.tokens) == 1
    assert session.tokens[0].creator_id == creator.id
    assert "token=" in captured["html"]


def test_verify_magic_link_token_returns_none_for_unknown_token():
    session = FakeSession()
    assert ml.verify_magic_link_token(session, "does-not-exist") is None


def test_verify_magic_link_token_returns_none_for_used_token():
    creator = _creator()
    token = MagicLinkToken(
        id=uuid.uuid4(),
        creator_id=creator.id,
        token="abc",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        used_at=datetime.now(UTC),
    )
    session = FakeSession(tokens=[token])
    assert ml.verify_magic_link_token(session, "abc") is None


def test_verify_magic_link_token_returns_none_for_expired_token():
    creator = _creator()
    token = MagicLinkToken(
        id=uuid.uuid4(),
        creator_id=creator.id,
        token="abc",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        used_at=None,
    )
    session = FakeSession(tokens=[token])
    assert ml.verify_magic_link_token(session, "abc") is None


def test_verify_magic_link_token_issues_session_and_marks_token_used():
    creator = _creator()
    token = MagicLinkToken(
        id=uuid.uuid4(),
        creator_id=creator.id,
        token="abc",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        used_at=None,
    )
    session = FakeSession(tokens=[token])

    result = ml.verify_magic_link_token(session, "abc")

    assert result is not None
    assert result.creator_id == creator.id
    assert token.used_at is not None
    assert result in session.sessions


def test_resolve_session_returns_none_for_expired_session():
    creator = _creator()
    session_row = SessionModel(
        id=uuid.uuid4(),
        creator_id=creator.id,
        token="sess-token",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    session = FakeSession(sessions=[session_row])
    assert ml.resolve_session(session, "sess-token") is None


def test_resolve_session_returns_session_for_valid_token():
    creator = _creator()
    session_row = SessionModel(
        id=uuid.uuid4(),
        creator_id=creator.id,
        token="sess-token",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session = FakeSession(sessions=[session_row])
    result = ml.resolve_session(session, "sess-token")
    assert result is session_row
