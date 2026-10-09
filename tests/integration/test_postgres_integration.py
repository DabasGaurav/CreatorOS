import pytest
from sqlalchemy import inspect

from creatorsignal.db.base import get_engine
from creatorsignal.niche.repository import add_niche_signal, list_niche_signal

pytestmark = pytest.mark.integration


def test_all_expected_tables_exist():
    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    assert {"creators", "reels", "reel_insights", "niche_signal", "creator_dna"} <= tables


def test_niche_signal_roundtrips_against_real_postgres(db_session):
    row = add_niche_signal(
        db_session,
        niche="__integration_test__",
        account_handle="@integration_test",
        observed_topic="temporary row from the automated integration suite",
        added_by="pytest",
    )
    try:
        results = list_niche_signal(db_session, niche="__integration_test__")
        assert any(r.id == row.id for r in results)
    finally:
        db_session.delete(row)
        db_session.commit()
