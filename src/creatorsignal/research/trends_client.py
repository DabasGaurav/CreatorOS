"""Google Trends via pytrends — unofficial, explicitly named by the spec as
fragile and non-core-path (B4). No API key needed, but treat failures as routine,
not exceptional: Google rate-limits/blocks this library often. The Market
Researcher must be able to skip this source silently-but-logged on failure.
"""

from pytrends.request import TrendReq

from creatorsignal.utils.logging import get_logger

logger = get_logger(__name__)


class TrendsUnavailable(Exception):
    """Raised on any pytrends failure — callers should treat this as 'skip this
    source', not a hard error, per the spec's fragility framing."""


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator else 0.0


def get_trend_data(
    query: str, *, client: TrendReq | None = None, timeframe: str = "today 3-m"
) -> dict:
    """Returns {query, slope, average_interest, data_points}. Raises
    TrendsUnavailable on any failure — Google Trends blocks/rate-limits often."""
    trends_client = client or TrendReq(hl="en-US", tz=360)
    try:
        trends_client.build_payload([query], timeframe=timeframe)
        df = trends_client.interest_over_time()
    except Exception as exc:
        logger.warning("pytrends failed for query %r: %s", query, exc)
        raise TrendsUnavailable(str(exc)) from exc

    if df is None or df.empty or query not in df.columns:
        return {"query": query, "slope": 0.0, "average_interest": 0.0, "data_points": 0}

    values = df[query].astype(float).tolist()
    return {
        "query": query,
        "slope": _linear_slope(values),
        "average_interest": sum(values) / len(values),
        "data_points": len(values),
    }
