import pytest

from creatorsignal.instagram import tester_admin


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(tester_admin, "_STORE_PATH", tmp_path / "tester_invites.json")


def test_record_invite_sent_marks_pending():
    record = tester_admin.record_invite_sent("@creator")
    assert record.status == tester_admin.InviteStatus.PENDING
    assert tester_admin.get_invite_status("@creator") == tester_admin.InviteStatus.PENDING


def test_record_invite_accepted_updates_status():
    tester_admin.record_invite_sent("@creator")
    record = tester_admin.record_invite_accepted("@creator")
    assert record.status == tester_admin.InviteStatus.ACCEPTED
    assert tester_admin.get_invite_status("@creator") == tester_admin.InviteStatus.ACCEPTED


def test_record_invite_accepted_without_prior_sent_still_records():
    record = tester_admin.record_invite_accepted("@new-creator")
    assert record.status == tester_admin.InviteStatus.ACCEPTED


def test_get_invite_status_returns_none_when_unknown():
    assert tester_admin.get_invite_status("@nobody") is None


def test_status_persists_across_separate_load_calls():
    tester_admin.record_invite_sent("@creator")
    # Simulate a second, independent CLI invocation reading the same file fresh.
    assert tester_admin.get_invite_status("@creator") == tester_admin.InviteStatus.PENDING
