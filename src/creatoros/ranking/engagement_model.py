"""Expected Engagement model (B9) — LightGBM learns a creator-specific mapping
from content characteristics to engagement rate.

Honesty note: the spec's B9 step 3 calls for "an initial category-level prior
model trained on whatever aggregate/public engagement benchmark data is
available." No such dataset was provided or sourced for this build — fabricating
synthetic "benchmark data" and training on it would misrepresent the model's
basis to the creator reading the Evidence Receipt. This ships honestly instead:

- With fewer than MIN_TRAINING_EXAMPLES real labeled examples (from a creator's
  own reel_insights — already real data per Build Doc 1), predict_expected_
  engagement returns a configured neutral prior. This *is* what spec B9 step 4
  describes: "ship it running on the category prior only" — the prior is just
  honestly a flat default rather than a benchmark-trained one, since no
  benchmark exists.
- Once a creator has enough of their own real history, a small LightGBM
  regressor trains directly on it (an empirical per-creator model — shrinkage
  toward a category prior is moot when the prior itself isn't from real data).
- train_expected_engagement_model is the retrain hook Build Doc 3's outcome
  loop calls as real published-Reel outcomes accumulate (B9 step 4, B16 step 4).

Leakage prevention (B9): every feature is computed as of the recommendation
timestamp and stored via feature_snapshots (Build Doc 2 schema) before this
model is ever called — never recomputed retroactively.
"""

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np

MIN_TRAINING_EXAMPLES = 10
DEFAULT_NEUTRAL_PRIOR = 0.5

FEATURE_ORDER = [
    "creator_fit",
    "audience_demand",
    "trend_momentum",
    "novelty",
    "posting_hour",
    "posting_weekday",
    "hook_type_code",
    "format_code",
]


@dataclass(frozen=True)
class TrainingRow:
    creator_fit: float
    audience_demand: float
    trend_momentum: float
    novelty: float
    posting_hour: int
    posting_weekday: int
    hook_type_code: int
    format_code: int
    engagement_rate: float


def _to_feature_vector(row) -> list[float]:
    return [getattr(row, name) for name in FEATURE_ORDER]


def train_expected_engagement_model(rows: list[TrainingRow]) -> lgb.Booster | None:
    """Returns None (cold-start mode) below MIN_TRAINING_EXAMPLES — LightGBM on
    single-digit rows overfits instantly and produces a model less trustworthy
    than the flat neutral prior it would replace."""
    if len(rows) < MIN_TRAINING_EXAMPLES:
        return None

    X = np.array([_to_feature_vector(r) for r in rows])
    y = np.array([r.engagement_rate for r in rows])

    train_data = lgb.Dataset(X, label=y, feature_name=FEATURE_ORDER)
    params = {
        "objective": "regression",
        "metric": "rmse",
        "num_leaves": 7,  # small — tiny per-creator datasets, avoid overfitting
        "min_data_in_leaf": 3,
        "verbose": -1,
    }
    return lgb.train(params, train_data, num_boost_round=50)


def predict_expected_engagement(
    model: lgb.Booster | None,
    features: dict,
    *,
    fallback_prior: float = DEFAULT_NEUTRAL_PRIOR,
) -> float:
    """features must carry every key in FEATURE_ORDER. Returns [0,1]-ish (an
    engagement-rate-scale prediction, clamped defensively since LightGBM
    regression has no output bound)."""
    if model is None:
        return fallback_prior

    vector = np.array([[features[name] for name in FEATURE_ORDER]])
    prediction = float(model.predict(vector)[0])
    return max(0.0, min(1.0, prediction))
