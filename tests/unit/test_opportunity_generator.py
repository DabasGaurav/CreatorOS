from creatorsignal.opportunity import opportunity_generator as og
from creatorsignal.opportunity.schemas import OpportunityCandidate, OpportunitySet
from creatorsignal.research.schemas import ResearchEvidence


def _evidence():
    return ResearchEvidence(
        niche="AI/startups",
        objective="grow reach",
        observations=[],
        final_reasoning="enough signal",
        confidence=0.7,
        exhausted_without_sufficient_evidence=False,
    )


def test_generate_opportunities_returns_candidates_from_structured_output(monkeypatch):
    candidates = [
        OpportunityCandidate(
            topic=f"topic {i}",
            angle="angle",
            audience_need="need",
            format="talking head",
            timing="now",
        )
        for i in range(20)
    ]

    captured = {}

    def fake_parse_structured(**kwargs):
        captured.update(kwargs)
        return OpportunitySet(candidates=candidates)

    monkeypatch.setattr(og, "parse_structured", fake_parse_structured)

    result = og.generate_opportunities(
        creator_dna={"winning_topics": []}, evidence=_evidence(), niche="AI/startups"
    )

    assert len(result) == 20
    assert result[0].topic == "topic 0"
    assert captured["output_format"] is OpportunitySet
    assert "AI/startups" in captured["messages"][0]["content"]
