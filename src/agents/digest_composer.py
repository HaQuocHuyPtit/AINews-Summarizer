import logging
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.schemas import SummarySchema

logger = logging.getLogger(__name__)

INTRO_PROMPT = """You are writing a brief introduction for a daily AI research digest email.
Given the list of paper categories and counts below, write 2-3 engaging sentences 
that preview the highlights. Keep it concise and exciting for software developers.

Categories and counts:
{categories}

Total papers: {total}

Write ONLY the introduction paragraph, nothing else."""

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class DigestComposer:
    """Agent that compiles paper summaries into a formatted HTML email digest."""

    def __init__(self):
        self.llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    def compose(self, summaries: List[SummarySchema]) -> str:
        # Group by category
        categories = defaultdict(list)
        for s in summaries:
            categories[s.category or "Other"].append(s)

        # Sort categories alphabetically
        sorted_categories = dict(sorted(categories.items()))

        # Generate intro via LLM
        intro = self._generate_intro(sorted_categories, len(summaries))

        # Render HTML template
        template = self.jinja_env.get_template("digest.html")
        html = template.render(
            date=date.today().strftime("%B %d, %Y"),
            intro=intro,
            categories=sorted_categories,
            total_papers=len(summaries),
        )

        logger.info("Composed digest with %d papers in %d categories",
                     len(summaries), len(sorted_categories))
        return html

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _generate_intro(self, categories: dict, total: int) -> str:
        cat_summary = "\n".join(f"- {cat}: {len(papers)} papers"
                                for cat, papers in categories.items())
        try:
            response = self.llm.invoke([
                SystemMessage(content="You write concise, engaging email introductions."),
                HumanMessage(content=INTRO_PROMPT.format(categories=cat_summary, total=total)),
            ])
            return response.content.strip()
        except Exception:
            logger.exception("Failed to generate intro, using fallback")
            return (f"Today's digest covers {total} new AI research papers "
                    f"across {len(categories)} categories. Let's dive in!")
