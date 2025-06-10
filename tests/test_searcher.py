from src.agents.paper_searcher import PaperSearcher


def test_search_arxiv_returns_papers():
    searcher = PaperSearcher(redis_client=None)
    papers = searcher._search_arxiv()
    assert len(papers) > 0
    for paper in papers:
        assert paper.title
        assert paper.url
        assert paper.source == "arxiv"
        assert paper.abstract


def test_search_dedup_by_url():
    searcher = PaperSearcher(redis_client=None)
    papers = searcher.search()
    urls = [p.url for p in papers]
    assert len(urls) == len(set(urls)), "Duplicate URLs found"
