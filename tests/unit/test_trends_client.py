import pandas as pd
import pytest

from creatoros.research import trends_client


def test_linear_slope_increasing_series():
    assert trends_client._linear_slope([10, 20, 30, 40]) > 0


def test_linear_slope_decreasing_series():
    assert trends_client._linear_slope([40, 30, 20, 10]) < 0


def test_linear_slope_flat_series():
    assert trends_client._linear_slope([10, 10, 10, 10]) == 0


def test_linear_slope_too_short():
    assert trends_client._linear_slope([5]) == 0.0
    assert trends_client._linear_slope([]) == 0.0


class FakeTrendReq:
    def __init__(self, df):
        self._df = df
        self.built = False

    def build_payload(self, kw_list, timeframe):
        self.built = True

    def interest_over_time(self):
        return self._df


def test_get_trend_data_returns_slope_and_average():
    df = pd.DataFrame({"AI agents": [10, 20, 30, 40], "isPartial": [False] * 4})
    client = FakeTrendReq(df)
    result = trends_client.get_trend_data("AI agents", client=client)
    assert client.built
    assert result["query"] == "AI agents"
    assert result["slope"] > 0
    assert result["average_interest"] == 25.0
    assert result["data_points"] == 4


def test_get_trend_data_empty_dataframe():
    client = FakeTrendReq(pd.DataFrame())
    result = trends_client.get_trend_data("obscure query", client=client)
    assert result["data_points"] == 0
    assert result["slope"] == 0.0


def test_get_trend_data_raises_trends_unavailable_on_failure():
    class FailingClient:
        def build_payload(self, kw_list, timeframe):
            raise RuntimeError("429 rate limited")

    with pytest.raises(trends_client.TrendsUnavailable):
        trends_client.get_trend_data("anything", client=FailingClient())
