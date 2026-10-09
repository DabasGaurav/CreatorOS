import pytest

from creatorsignal.utils.retry import with_backoff


class FlakyError(Exception):
    pass


def test_with_backoff_retries_until_success():
    calls = {"n": 0}

    @with_backoff(exceptions=(FlakyError,), max_attempts=3, initial=0.001, max_wait=0.01)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FlakyError("not yet")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_with_backoff_reraises_after_max_attempts():
    calls = {"n": 0}

    @with_backoff(exceptions=(FlakyError,), max_attempts=2, initial=0.001, max_wait=0.01)
    def always_fails():
        calls["n"] += 1
        raise FlakyError("nope")

    with pytest.raises(FlakyError):
        always_fails()
    assert calls["n"] == 2


def test_with_backoff_does_not_catch_other_exceptions():
    @with_backoff(exceptions=(FlakyError,), max_attempts=3, initial=0.001, max_wait=0.01)
    def wrong_error():
        raise ValueError("unrelated")

    with pytest.raises(ValueError):
        wrong_error()
