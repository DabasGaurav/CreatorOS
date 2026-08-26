from creatoros.content import content_generator as cg
from creatoros.content import reranker as rr
from creatoros.content.schemas import ContentPackage, RerankerOutput
from creatoros.opportunity.schemas import OpportunityCandidate
from creatoros.research.schemas import ResearchEvidence


def _candidate():
    return OpportunityCandidate(
        topic="AI agents replacing junior developers",
        angle="employment impact",
        audience_need="career anxiety about AI",
        format="talking head",
        timing="trending now",
    )


def _evidence():
    return ResearchEvidence(
        niche="AI/startups",
        objective="grow reach",
        observations=[],
        final_reasoning="strong signal",
        confidence=0.8,
        exhausted_without_sufficient_evidence=False,
    )


def test_rerank_and_explain_calls_sonnet_and_returns_narrative(monkeypatch):
    captured = {}

    def fake_parse_structured(**kwargs):
        captured.update(kwargs)
        return RerankerOutput(why_now="because trends", why_you="matches your DNA")

    monkeypatch.setattr(rr, "parse_structured", fake_parse_structured)

    result = rr.rerank_and_explain(
        selected_candidate=_candidate(), evidence=_evidence(), creator_dna={"winning_topics": []}
    )

    assert result.why_now == "because trends"
    assert captured["model"] == rr.get_settings().model_sonnet
    assert captured["output_format"] is RerankerOutput
    assert "temperature" not in captured  # Sonnet 5 rejects this param — see module docstring


def test_generate_content_package_calls_sonnet_and_returns_package(monkeypatch):
    def fake_parse_structured(**kwargs):
        return ContentPackage(
            hook="hook text",
            script="script text",
            storyboard="storyboard text",
            caption="caption text",
            cta="cta text",
        )

    monkeypatch.setattr(cg, "parse_structured", fake_parse_structured)

    result = cg.generate_content_package(
        selected_candidate=_candidate(), evidence=_evidence(), creator_dna={"winning_topics": []}
    )

    assert result.hook == "hook text"
    assert result.cta == "cta text"
