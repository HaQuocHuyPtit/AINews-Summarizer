from src.agents.digest_composer import DigestComposer
from src.models.schemas import SummarySchema


def test_compose_digest():
    """Requires Ollama running with the configured model."""
    composer = DigestComposer()
    summaries = [
        SummarySchema(
            title="Paper A",
            summary="This paper introduces a new NLP technique.",
            category="NLP",
            url="https://example.com/a",
        ),
        SummarySchema(
            title="Paper B",
            summary="This paper proposes a computer vision model.",
            category="Computer Vision",
            url="https://example.com/b",
        ),
    ]
    html = composer.compose(summaries)
    assert "<html>" in html
    assert "Paper A" in html
    assert "Paper B" in html
    assert "NLP" in html
    assert "Computer Vision" in html
