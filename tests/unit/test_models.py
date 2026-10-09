from creatorsignal.db.base import Base
from creatorsignal.db.models import CreatorDNA, NicheSignal, Reel, ReelInsight


def test_expected_tables_registered():
    assert set(Base.metadata.tables) == {
        "creators",
        "reels",
        "reel_insights",
        "niche_signal",
        "creator_dna",
        "recommendations",
        "feature_snapshots",
        "external_result_cache",
        "outcomes",
        "magic_link_tokens",
        "sessions",
    }


def test_reel_unique_constraint_on_creator_and_media_id():
    reel_table = Base.metadata.tables["reels"]
    constraint_columns = {
        tuple(c.name for c in uc.columns) for uc in reel_table.constraints if hasattr(uc, "columns")
    }
    assert ("creator_id", "instagram_media_id") in constraint_columns


def test_creator_dna_unique_constraint_on_creator_and_version():
    dna_table = Base.metadata.tables["creator_dna"]
    constraint_columns = {
        tuple(c.name for c in uc.columns) for uc in dna_table.constraints if hasattr(uc, "columns")
    }
    assert ("creator_id", "version") in constraint_columns


def test_creator_dna_has_early_profile_flag():
    assert "early_profile" in CreatorDNA.__table__.columns


def test_reel_insights_has_surrogate_primary_key_and_raw_json():
    columns = ReelInsight.__table__.columns
    assert "id" in columns
    assert "raw_insights_json" in columns


def test_niche_signal_matches_spec_columns():
    expected = {
        "id",
        "niche",
        "account_handle",
        "observed_topic",
        "note",
        "observed_at",
        "added_by",
    }
    assert set(NicheSignal.__table__.columns.keys()) == expected


def test_reel_has_raw_media_json_and_extracted_metadata_fields():
    columns = Reel.__table__.columns
    for col in ("raw_media_json", "duration_seconds", "media_product_type"):
        assert col in columns
