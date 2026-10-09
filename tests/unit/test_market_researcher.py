from creatorsignal.research import market_researcher as mr
from creatorsignal.research.schemas import ResearchStep
from creatorsignal.research.youtube_client import YouTubeNotConfigured


class FakeSession:
    def __init__(self):
        self.rows = {}

    def get(self, model, key):
        return self.rows.get(key)

    def add(self, row):
        self.rows[row.cache_key] = row

    def commit(self):
        pass


def test_stops_immediately_when_first_step_reports_sufficient():
    calls = {"n": 0}

    def fake_call_step(niche, objective, observations):
        calls["n"] += 1
        return ResearchStep(
            sufficient=True,
            confidence=0.8,
            reasoning="Enough signal already",
            next_source="youtube",
            next_query="unused",
        )

    session = FakeSession()
    evidence = mr.run_market_researcher(
        session, niche="AI/startups", objective="grow reach", call_step=fake_call_step
    )

    assert calls["n"] == 1
    assert evidence.exhausted_without_sufficient_evidence is False
    assert evidence.observations == []
    assert evidence.confidence == 0.8


def test_hard_iteration_cap_enforced_regardless_of_llm_output(monkeypatch):
    monkeypatch.setattr(
        mr,
        "search_videos",
        lambda query: (_ for _ in ()).throw(YouTubeNotConfigured("no key")),
    )

    calls = {"n": 0}

    def always_insufficient(niche, objective, observations):
        calls["n"] += 1
        return ResearchStep(
            sufficient=False,
            confidence=0.1,
            reasoning="still not enough",
            next_source="youtube",
            next_query="query",
        )

    session = FakeSession()
    evidence = mr.run_market_researcher(
        session,
        niche="AI/startups",
        objective="grow reach",
        max_iterations=3,
        call_step=always_insufficient,
    )

    assert calls["n"] == 3  # never exceeds the cap, no matter what the LLM says
    assert evidence.exhausted_without_sufficient_evidence is True
    assert len(evidence.observations) == 3


def test_dispatches_to_correct_source_and_records_observation(monkeypatch):
    monkeypatch.setattr(mr, "search_videos", lambda query: {"pageInfo": {"totalResults": 500}})

    def call_step(niche, objective, observations):
        if observations:
            return ResearchStep(
                sufficient=True,
                confidence=0.7,
                reasoning="done",
                next_source="youtube",
                next_query="",
            )
        return ResearchStep(
            sufficient=False,
            confidence=0.2,
            reasoning="need data",
            next_source="youtube",
            next_query="AI coding agents",
        )

    session = FakeSession()
    evidence = mr.run_market_researcher(
        session, niche="AI/startups", objective="grow reach", call_step=call_step
    )

    assert len(evidence.observations) == 1
    obs = evidence.observations[0]
    assert obs.source == "youtube"
    assert obs.succeeded is True
    assert "500" in obs.raw_result_summary


def test_unconfigured_source_recorded_as_failed_observation_not_a_crash(monkeypatch):
    monkeypatch.setattr(
        mr,
        "search_videos",
        lambda query: (_ for _ in ()).throw(YouTubeNotConfigured("no key")),
    )

    def call_step(niche, objective, observations):
        return ResearchStep(
            sufficient=False,
            confidence=0.1,
            reasoning="trying youtube",
            next_source="youtube",
            next_query="query",
        )

    session = FakeSession()
    evidence = mr.run_market_researcher(
        session, niche="AI/startups", objective="grow reach", max_iterations=1, call_step=call_step
    )

    assert evidence.observations[0].succeeded is False
    assert "unavailable" in evidence.observations[0].raw_result_summary


def test_unexpected_source_exception_recorded_as_failed_not_a_crash(monkeypatch):
    # Not YouTubeNotConfigured/RedditNotConfigured/TrendsUnavailable — a generic
    # failure (e.g. a misconfigured Reddit app returning 403 during OAuth), which
    # a real live run showed previously propagated uncaught and killed the whole
    # LangGraph node.
    monkeypatch.setattr(
        mr, "search_videos", lambda query: (_ for _ in ()).throw(RuntimeError("403 Forbidden"))
    )

    def call_step(niche, objective, observations):
        return ResearchStep(
            sufficient=False,
            confidence=0.1,
            reasoning="trying youtube",
            next_source="youtube",
            next_query="query",
        )

    session = FakeSession()
    evidence = mr.run_market_researcher(
        session, niche="AI/startups", objective="grow reach", max_iterations=1, call_step=call_step
    )

    assert evidence.observations[0].succeeded is False
    assert "failed" in evidence.observations[0].raw_result_summary


def test_cache_avoids_second_external_call_for_same_query(monkeypatch):
    call_count = {"n": 0}

    def fake_search_videos(query):
        call_count["n"] += 1
        return {"pageInfo": {"totalResults": 100}}

    monkeypatch.setattr(mr, "search_videos", fake_search_videos)

    session = FakeSession()
    mr._call_source(session, "youtube", "same query")
    mr._call_source(session, "youtube", "same query")

    assert call_count["n"] == 1  # second call served from cache
