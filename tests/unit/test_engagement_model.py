import random

from creatoros.ranking.engagement_model import (
    DEFAULT_NEUTRAL_PRIOR,
    MIN_TRAINING_EXAMPLES,
    TrainingRow,
    predict_expected_engagement,
    train_expected_engagement_model,
)


def _row(engagement_rate, **overrides):
    defaults = dict(
        creator_fit=0.5,
        audience_demand=0.5,
        trend_momentum=0.5,
        novelty=0.5,
        posting_hour=12,
        posting_weekday=2,
        hook_type_code=0,
        format_code=0,
        engagement_rate=engagement_rate,
    )
    defaults.update(overrides)
    return TrainingRow(**defaults)


def test_train_returns_none_below_minimum_examples():
    rows = [_row(0.1) for _ in range(MIN_TRAINING_EXAMPLES - 1)]
    assert train_expected_engagement_model(rows) is None


def test_predict_returns_fallback_prior_with_no_model():
    features = {
        "creator_fit": 0.5,
        "audience_demand": 0.5,
        "trend_momentum": 0.5,
        "novelty": 0.5,
        "posting_hour": 12,
        "posting_weekday": 2,
        "hook_type_code": 0,
        "format_code": 0,
    }
    assert predict_expected_engagement(None, features) == DEFAULT_NEUTRAL_PRIOR
    assert predict_expected_engagement(None, features, fallback_prior=0.3) == 0.3


def test_train_and_predict_roundtrip_with_enough_data():
    rng = random.Random(0)
    rows = []
    for _ in range(30):
        creator_fit = rng.random()
        # Engineer a clean signal: engagement scales with creator_fit.
        rows.append(_row(engagement_rate=creator_fit * 0.5, creator_fit=creator_fit))

    model = train_expected_engagement_model(rows)
    assert model is not None

    high_fit_features = {
        "creator_fit": 0.9,
        "audience_demand": 0.5,
        "trend_momentum": 0.5,
        "novelty": 0.5,
        "posting_hour": 12,
        "posting_weekday": 2,
        "hook_type_code": 0,
        "format_code": 0,
    }
    low_fit_features = dict(high_fit_features, creator_fit=0.1)

    high_pred = predict_expected_engagement(model, high_fit_features)
    low_pred = predict_expected_engagement(model, low_fit_features)
    assert high_pred > low_pred


def test_predict_clamps_output_to_unit_interval():
    # Even with a trained model, defensively clamp — LightGBM regression has no
    # inherent output bound.
    rows = [_row(engagement_rate=0.05, creator_fit=i / 40) for i in range(20)]
    model = train_expected_engagement_model(rows)
    features = {
        "creator_fit": 1.0,
        "audience_demand": 1.0,
        "trend_momentum": 1.0,
        "novelty": 1.0,
        "posting_hour": 12,
        "posting_weekday": 2,
        "hook_type_code": 0,
        "format_code": 0,
    }
    prediction = predict_expected_engagement(model, features)
    assert 0.0 <= prediction <= 1.0
