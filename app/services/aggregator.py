import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.scrapers.youtube_scraper import YouTubeScraper
from app.scrapers.serp_scraper import SerpScraper
from app.scrapers.reddit_scraper import RedditScraper
from app.scrapers.blog_forum_scraper import BlogForumScraper
import logging

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)


class DataAggregator:

    def __init__(self):
        self.youtube    = YouTubeScraper()
        self.serp       = SerpScraper()
        self.reddit     = RedditScraper()
        self.blog_forum = BlogForumScraper()

    async def gather_all(self, query: str, country: str) -> dict:
        loop = asyncio.get_event_loop()

        yt_task     = loop.run_in_executor(executor, self.youtube.fetch,    query, country)
        serp_task   = loop.run_in_executor(executor, self.serp.fetch,       query, country)
        reddit_task = loop.run_in_executor(executor, self.reddit.fetch,     query, country)
        blog_task   = loop.run_in_executor(executor, self.blog_forum.fetch, query, country)

        yt, serp_data, reddit, blog = await asyncio.gather(
            yt_task, serp_task, reddit_task, blog_task,
            return_exceptions=True,
        )

        def safe(result, source_name: str) -> list:
            if isinstance(result, list):
                return result
            if isinstance(result, Exception):
                logger.warning(f"Scraper '{source_name}' failed: {result}")
            return []

        serp_items        = []
        serp_related      = []
        serp_paa          = []
        serp_pas          = []
        serp_autocomplete = []
        # NEW: rich SERP features
        serp_immersive_products  = []
        serp_more_products       = []
        serp_inline_videos       = []
        serp_more_videos         = []
        serp_refine_searches     = []
        serp_ai_overview_text    = []
        serp_ai_overview_refs    = []

        if isinstance(serp_data, dict):
            serp_items               = serp_data.get("results", [])
            serp_related             = serp_data.get("related_searches", [])
            serp_paa                 = serp_data.get("people_also_ask", [])
            serp_pas                 = serp_data.get("people_also_search_for", [])
            serp_autocomplete        = serp_data.get("autocomplete", [])
            serp_immersive_products  = serp_data.get("immersive_products", [])
            serp_more_products       = serp_data.get("more_products", [])
            serp_inline_videos       = serp_data.get("inline_videos", [])
            serp_more_videos         = serp_data.get("more_videos", [])
            serp_refine_searches     = serp_data.get("refine_searches", [])
            serp_ai_overview_text    = serp_data.get("ai_overview_text", [])
            serp_ai_overview_refs    = serp_data.get("ai_overview_references", [])

        for item in serp_items:
            item["source"] = "serp"

        yt_items     = safe(yt,     "youtube")
        reddit_items = safe(reddit, "reddit")
        blog_items   = safe(blog,   "blog_forum")

        all_items    = yt_items + serp_items + reddit_items + blog_items
        sources_used = list({item.get("source", "unknown") for item in all_items})

        serp_urls   = [i.get("url") for i in serp_items   if i.get("url")]
        yt_urls     = [i.get("url") for i in yt_items     if i.get("url")]
        reddit_urls = [i.get("url") for i in reddit_items if i.get("url")]
        blog_urls   = [i.get("url") for i in blog_items   if i.get("url")]
        source_urls = serp_urls + yt_urls + reddit_urls + blog_urls

        logger.info(
            f"Aggregator | items={len(all_items)} sources={sources_used} "
            f"related={len(serp_related)} paa={len(serp_paa)} pas={len(serp_pas)} "
            f"autocomplete={len(serp_autocomplete)} "
            f"immersive={len(serp_immersive_products)} "
            f"inline_videos={len(serp_inline_videos)} "
            f"ai_overview_refs={len(serp_ai_overview_refs)}"
        )

        return {
            "items":                  all_items,
            "sources_used":           sources_used,
            "source_urls":            source_urls,
            "serp_related_searches":  serp_related,
            "people_also_ask":        serp_paa,
            "people_also_search_for": serp_pas,
            "autocomplete":           serp_autocomplete,
            "immersive_products":     serp_immersive_products,
            "more_products":          serp_more_products,
            "inline_videos":          serp_inline_videos,
            "more_videos":            serp_more_videos,
            "refine_searches":        serp_refine_searches,
            "ai_overview_text":       serp_ai_overview_text,
            "ai_overview_references": serp_ai_overview_refs,
        }

    def build_context_text(self, items: list[dict]) -> str:
        lines = []
        for item in items[:25]:
            source = item.get("source", "unknown").upper()
            title  = item.get("title",  "").strip()
            desc   = item.get("description", "").strip()[:200]
            if title:
                lines.append(f"[{source}] Title: {title}")
            if desc:
                lines.append(f"Description: {desc}")
        return "\n".join(lines)

    def build_source_context(self, items: list[dict], source: str) -> str:
        lines = []
        for item in items:
            if item.get("source", "").lower() != source.lower():
                continue
            title = item.get("title", "").strip()
            desc  = item.get("description", "").strip()[:300]
            url   = item.get("url", "")
            if title:
                lines.append(f"Title: {title}")
            if desc:
                lines.append(f"Snippet: {desc}")
            if url:
                lines.append(f"URL: {url}")
        return "\n".join(lines)