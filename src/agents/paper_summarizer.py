import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.schemas import PaperSchema, SummarySchema

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI research expert who makes complex topics accessible.
Given a research paper's title and abstract, do two things:

1. Write a 2-3 sentence summary in plain English that a software developer can understand.
   Focus on the key contribution and why it matters. Avoid jargon.

2. Categorize the paper into exactly ONE of these categories:
   NLP, Computer Vision, Reinforcement Learning, LLMs, Multimodal, Robotics, 
   AI Safety, Optimization, Other

Respond in this exact format:
CATEGORY: <category>
SUMMARY: <your summary>"""


class PaperSummarizer:
    """Agent that summarizes research papers using a local LLM via Ollama."""

    def __init__(self):
        self.llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )

    def summarize_all(self, papers: List[PaperSchema]) -> List[SummarySchema]:
        summaries = []
        for i, paper in enumerate(papers):
            logger.info("Summarizing paper %d/%d: %s", i + 1, len(papers), paper.title)
            summary = self._summarize_one(paper)
            if summary:
                summaries.append(summary)
        logger.info("Summarized %d/%d papers", len(summaries), len(papers))
        return summaries

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _summarize_one(self, paper: PaperSchema) -> SummarySchema | None:
        try:
            response = self.llm.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"Title: {paper.title}\n\nAbstract: {paper.abstract}"),
            ])
            content = response.content

            # Parse category and summary from response
            category = "Other"
            summary_text = content

            lines = content.strip().split("\n")
            for line in lines:
                if line.startswith("CATEGORY:"):
                    category = line.replace("CATEGORY:", "").strip()
                elif line.startswith("SUMMARY:"):
                    summary_text = line.replace("SUMMARY:", "").strip()

            # If SUMMARY: wasn't on a single line, get everything after it
            if "SUMMARY:" in content:
                summary_text = content.split("SUMMARY:", 1)[1].strip()

            return SummarySchema(
                title=paper.title,
                summary=summary_text,
                category=category,
                url=paper.url,
            )
        except Exception:
            logger.exception("Failed to summarize paper: %s", paper.title)
            return None
