from datetime import datetime

from creatorsignal.ranking.feature_engineering import (
    build_feature_dict,
    encode_format,
    encode_hook_type,
)


def test_encode_hook_type_stable_and_distinct():
    assert encode_hook_type("pov") != encode_hook_type("listicle")
    assert encode_hook_type("pov") == encode_hook_type("pov")


def test_encode_hook_type_unknown_value_gets_own_code():
    known_codes = {encode_hook_type("pov"), encode_hook_type("listicle")}
    unseen_code = encode_hook_type("some_new_hook_type")
    assert unseen_code not in known_codes


def test_encode_hook_type_none():
    assert isinstance(encode_hook_type(None), int)


def test_encode_format_stable_and_distinct():
    assert encode_format("short_form_quick_hit") != encode_format("long_form")


def test_build_feature_dict_has_all_expected_keys():
    features = build_feature_dict(
        creator_fit=0.8,
        audience_demand=0.5,
        trend_momentum=0.3,
        novelty=0.7,
        hook_type="pov",
        format_tag="short_form_quick_hit",
        posting_time=datetime(2026, 1, 15, 14, 30),
    )
    assert features["creator_fit"] == 0.8
    assert features["posting_hour"] == 14
    assert features["posting_weekday"] == datetime(2026, 1, 15).weekday()
    assert features["hook_type_code"] == encode_hook_type("pov")
    assert features["format_code"] == encode_format("short_form_quick_hit")
