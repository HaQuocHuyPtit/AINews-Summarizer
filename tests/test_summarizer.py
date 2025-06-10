from src.agents.paper_summarizer import PaperSummarizer
from src.models.schemas import PaperSchema


def test_summarize_one_paper():
    """Requires Ollama running with the configured model."""
    summarizer = PaperSummarizer()
    paper = PaperSchema(
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        abstract=(
            "The dominant sequence transduction models are based on complex recurrent or "
            "convolutional neural networks that include an encoder and a decoder. The best "
            "performing models also connect the encoder and decoder through an attention "
            "mechanism. We propose a new simple network architecture, the Transformer, "
            "based solely on attention mechanisms, dispensing with recurrence and convolutions "
            "entirely."
        ),
        url="https://arxiv.org/abs/1706.03762",
        source="arxiv",
    )
    result = summarizer._summarize_one(paper)
    assert result is not None
    assert result.summary
    assert result.category
    assert result.url == paper.url
