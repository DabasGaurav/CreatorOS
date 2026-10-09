from types import SimpleNamespace

from creatorsignal.outcome import outcome_tracking as ot


def test_remap_cosine_to_unit_clamps():
    assert ot._remap_cosine_to_unit(1.0) == 1.0
    assert ot._remap_cosine_to_unit(-1.0) == 0.0
    assert ot._remap_cosine_to_unit(0.0) == 0.5


def test_topic_match_score_none_when_no_reel_text():
    recommendation = SimpleNamespace(topic="AI tools", angle="productivity")
    reel = SimpleNamespace(caption=None, transcript=None)
    assert ot._topic_match_score(recommendation, reel) is None


def test_topic_match_score_none_when_no_recommendation_topic():
    recommendation = SimpleNamespace(topic=None, angle=None)
    reel = SimpleNamespace(caption="some caption", transcript=None)
    assert ot._topic_match_score(recommendation, reel) is None


def test_topic_match_score_high_for_similar_text(monkeypatch):
    def fake_embed_text(text, input_type="query"):
        return [1.0, 0.0] if "AI tools" in text else [1.0, 0.0]

    monkeypatch.setattr(ot, "embed_text", fake_embed_text)
    recommendation = SimpleNamespace(topic="AI tools", angle="productivity")
    reel = SimpleNamespace(caption="AI tools for productivity", transcript=None)

    score = ot._topic_match_score(recommendation, reel)
    assert score == 1.0


def test_topic_match_score_uses_caption_and_transcript_combined(monkeypatch):
    captured = []

    def fake_embed_text(text, input_type="query"):
        captured.append(text)
        return [1.0, 0.0]

    monkeypatch.setattr(ot, "embed_text", fake_embed_text)
    recommendation = SimpleNamespace(topic="AI tools", angle="productivity")
    reel = SimpleNamespace(caption="caption text", transcript="transcript text")

    ot._topic_match_score(recommendation, reel)
    assert captured[0] == "caption text transcript text"
