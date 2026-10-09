from types import SimpleNamespace

from creatorsignal.embeddings import voyage_client


def test_build_reel_embedding_text_joins_caption_and_transcript():
    text = voyage_client.build_reel_embedding_text(
        caption="caption here", transcript="transcript here"
    )
    assert "caption here" in text
    assert "transcript here" in text


def test_build_reel_embedding_text_handles_missing_transcript():
    text = voyage_client.build_reel_embedding_text(caption="only caption", transcript=None)
    assert text == "only caption"


def test_build_reel_embedding_text_handles_both_missing():
    assert voyage_client.build_reel_embedding_text(caption=None, transcript=None) == ""


def test_embed_texts_calls_voyage_client_and_returns_embeddings(monkeypatch):
    captured = {}

    class FakeVoyageClient:
        def embed(self, texts, model=None, input_type=None):
            captured["texts"] = texts
            captured["model"] = model
            captured["input_type"] = input_type
            return SimpleNamespace(embeddings=[[0.1, 0.2, 0.3] for _ in texts])

    monkeypatch.setattr(voyage_client, "_client", lambda: FakeVoyageClient())

    result = voyage_client.embed_texts(["hello", "world"])
    assert result == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert captured["texts"] == ["hello", "world"]
    assert captured["input_type"] == "document"


def test_embed_text_returns_single_vector(monkeypatch):
    class FakeVoyageClient:
        def embed(self, texts, model=None, input_type=None):
            return SimpleNamespace(embeddings=[[1.0, 2.0]])

    monkeypatch.setattr(voyage_client, "_client", lambda: FakeVoyageClient())

    assert voyage_client.embed_text("hello") == [1.0, 2.0]
