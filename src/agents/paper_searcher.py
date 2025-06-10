import logging
from datetime import datetime, timedelta
from typing import List

import requests
import xmltodict
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.schemas import PaperSchema

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# arXiv categories for AI/ML research
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.MA"]


class PaperSearcher:
    """Agent that searches for recent AI research papers from arXiv and Semantic Scholar."""

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def search(self) -> List[PaperSchema]:
        papers = []
        papers.extend(self._search_arxiv())
        papers.extend(self._search_semantic_scholar())

        # Dedup by URL
        seen_urls = set()
        unique_papers = []
        for paper in papers:
            if paper.url not in seen_urls:
                seen_urls.add(paper.url)
                # Check Redis dedup cache
                if self.redis and self.redis.exists(f"paper:{paper.url}"):
                    logger.debug("Skipping already-seen paper: %s", paper.title)
                    continue
                unique_papers.append(paper)
                # Cache in Redis for 7 days
                if self.redis:
                    self.redis.setex(f"paper:{paper.url}", timedelta(days=7), "1")

        logger.info("Found %d unique new papers", len(unique_papers))
        return unique_papers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _search_arxiv(self) -> List[PaperSchema]:
        logger.info("Searching arXiv for recent AI papers...")
        category_query = " OR ".join(f"cat:{cat}" for cat in ARXIV_CATEGORIES)
        params = {
            "search_query": category_query,
            "start": 0,
            "max_results": settings.arxiv_max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        response = requests.get(ARXIV_API_URL, params=params, timeout=30)
        response.raise_for_status()

        feed = xmltodict.parse(response.text)
        entries = feed.get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]

        papers = []
        for entry in entries:
            authors_raw = entry.get("author", [])
            if isinstance(authors_raw, dict):
                authors_raw = [authors_raw]
            authors = [a.get("name", "") for a in authors_raw]

            published_str = entry.get("published", "")
            published_at = None
            if published_str:
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            # Get the abstract link
            links = entry.get("link", [])
            if isinstance(links, dict):
                links = [links]
            url = ""
            for link in links:
                if link.get("@type") == "text/html":
                    url = link.get("@href", "")
                    break
            if not url:
                url = entry.get("id", "")

            papers.append(PaperSchema(
                title=entry.get("title", "").replace("\n", " ").strip(),
                authors=authors,
                abstract=entry.get("summary", "").replace("\n", " ").strip(),
                url=url,
                source="arxiv",
                published_at=published_at,
            ))

        logger.info("Found %d papers from arXiv", len(papers))
        return papers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _search_semantic_scholar(self) -> List[PaperSchema]:
        logger.info("Searching Semantic Scholar for trending AI papers...")
        params = {
            "query": "artificial intelligence machine learning",
            "limit": settings.semantic_scholar_max_results,
            "fields": "title,authors,abstract,url,publicationDate",
            "sort": "publicationDate:desc",
        }

        try:
            response = requests.get(SEMANTIC_SCHOLAR_API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception:
            logger.warning("Semantic Scholar search failed, skipping")
            return []

        papers = []
        for item in data.get("data", []):
            if not item.get("abstract"):
                continue

            authors = [a.get("name", "") for a in (item.get("authors") or [])]
            published_at = None
            if item.get("publicationDate"):
                try:
                    published_at = datetime.fromisoformat(item["publicationDate"])
                except ValueError:
                    pass

            papers.append(PaperSchema(
                title=item.get("title", ""),
                authors=authors,
                abstract=item.get("abstract", ""),
                url=item.get("url") or f"https://api.semanticscholar.org/graph/v1/paper/{item.get('paperId', '')}",
                source="semantic_scholar",
                published_at=published_at,
            ))

        logger.info("Found %d papers from Semantic Scholar", len(papers))
        return papers
