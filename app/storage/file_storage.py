import os
import json
import csv
import logging
import time
from datetime import datetime
from app.config import get_settings
from app.models.schemas import GeneratedContent, ProcessedInsights

logger = logging.getLogger(__name__)


def _ensure_dirs():
    s = get_settings()
    os.makedirs(s.CSV_DIR, exist_ok=True)
    os.makedirs(s.JSON_DIR, exist_ok=True)


def _safe_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")[:40]


def _safe_write_file(filepath, content_func):
    """Executes a file write operation with retries to resolve Windows sharing/lock violations gracefully."""
    for attempt in range(5):
        try:
            content_func(filepath)
            return
        except PermissionError as e:
            if attempt == 4:
                raise e
            time.sleep(0.2)


def _insights_dict(insights: ProcessedInsights) -> dict:
    """Centralised serialisation — save and update always stay in sync."""
    return {
        "keywords":               insights.keywords,
        "autocomplete_keywords":  insights.autocomplete_keywords,
        "keyword_clusters":       insights.keyword_clusters,
        "keyword_difficulty":     insights.keyword_difficulty,
        "reddit_trends":          insights.reddit_trends,
        "youtube_trends":         insights.youtube_trends,
        "people_also_ask":        insights.people_also_ask,
        "people_also_search_for": insights.people_also_search_for,
        "trending_topics":        insights.trending_topics,
        "faqs":                   insights.faqs,
        "market_trends":          insights.market_trends,
        # SERP rich features
        "immersive_products":     insights.immersive_products,
        "more_products":          insights.more_products,
        "inline_videos":          insights.inline_videos,
        "more_videos":            insights.more_videos,
        "refine_searches":        insights.refine_searches,
        "ai_overview_text":       insights.ai_overview_text,
        "ai_overview_references": insights.ai_overview_references,
    }


def _load_insights(saved: dict) -> dict:
    """Load insights dict from JSON — provides defaults for all fields."""
    return {
        "keywords":               saved.get("keywords", []),
        "autocomplete_keywords":  saved.get("autocomplete_keywords", []),
        "keyword_clusters":       saved.get("keyword_clusters", []),
        "keyword_difficulty":     saved.get("keyword_difficulty", {}),
        "reddit_trends":          saved.get("reddit_trends", []),
        "youtube_trends":         saved.get("youtube_trends", []),
        "people_also_ask":        saved.get("people_also_ask", []),
        "people_also_search_for": saved.get("people_also_search_for", []),
        "trending_topics":        saved.get("trending_topics", []),
        "faqs":                   saved.get("faqs", []),
        "market_trends":          saved.get("market_trends", []),
        "immersive_products":     saved.get("immersive_products", []),
        "more_products":          saved.get("more_products", []),
        "inline_videos":          saved.get("inline_videos", []),
        "more_videos":            saved.get("more_videos", []),
        "refine_searches":        saved.get("refine_searches", []),
        "ai_overview_text":       saved.get("ai_overview_text", []),
        "ai_overview_references": saved.get("ai_overview_references", []),
    }


# ── JSON Storage ──────────────────────────────────────────────────────────────

def save_content_json(content: GeneratedContent) -> str:
    _ensure_dirs()
    s = get_settings()
    filename = f"{_safe_name(content.name)}_{content.id[:8]}.json"
    filepath = os.path.join(s.JSON_DIR, filename)

    data = {
        "id":                    content.id,
        "name":                  content.name,
        "content_type":          content.content_type,
        "country":               content.country,
        "created_at":            content.created_at.isoformat(),
        "refresh_interval":      content.refresh_interval,
        "custom_interval_hours": content.custom_interval_hours,
        "next_refresh_at":       content.next_refresh_at.isoformat() if content.next_refresh_at else None,
        "sources_used":          content.sources_used,
        "source_urls":           content.source_urls,
        "sections":              [{"heading": s.heading, "body": s.body} for s in content.sections],
        "insights":              _insights_dict(content.insights),
        "metadata": {
            "total_headings":      len(content.sections),
            "sources_count":       len(content.source_urls),
            "keywords_extracted":  len(content.insights.keywords),
            "people_also_ask":     len(content.insights.people_also_ask),
            "people_also_search":  len(content.insights.people_also_search_for),
            "autocomplete":        len(content.insights.autocomplete_keywords),
            "immersive_products":  len(content.insights.immersive_products),
            "inline_videos":       len(content.insights.inline_videos),
        }
    }

    def write_json(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    _safe_write_file(filepath, write_json)

    logger.info(f"Content JSON saved: {filepath}")
    return filepath


def load_content_json(content_id: str) -> dict | None:
    _ensure_dirs()
    s = get_settings()
    for filename in os.listdir(s.JSON_DIR):
        if filename.endswith(".json") and content_id[:8] in filename:
            filepath = os.path.join(s.JSON_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def list_all_content_json() -> list[dict]:
    _ensure_dirs()
    s = get_settings()
    results = []
    for filename in os.listdir(s.JSON_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(s.JSON_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to read {filename}: {e}")
    return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)


def update_content_json(content: GeneratedContent) -> str:
    _ensure_dirs()
    s = get_settings()
    for filename in os.listdir(s.JSON_DIR):
        if filename.endswith(".json") and content.id[:8] in filename:
            filepath = os.path.join(s.JSON_DIR, filename)
            data = {
                "id":                    content.id,
                "name":                  content.name,
                "content_type":          content.content_type,
                "country":               content.country,
                "created_at":            content.created_at.isoformat(),
                "refresh_interval":      content.refresh_interval,
                "custom_interval_hours": content.custom_interval_hours,
                "next_refresh_at":       content.next_refresh_at.isoformat() if content.next_refresh_at else None,
                "sources_used":          content.sources_used,
                "sections":              [{"heading": s.heading, "body": s.body} for s in content.sections],
                "insights":              _insights_dict(content.insights),
                "metadata": {
                    "last_refreshed":     datetime.utcnow().isoformat(),
                    "total_headings":     len(content.sections),
                    "immersive_products": len(content.insights.immersive_products),
                }
            }
            def write_json(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            _safe_write_file(filepath, write_json)
            return filepath
    return save_content_json(content)


# ── CSV Storage ───────────────────────────────────────────────────────────────

def save_keywords_csv(
    content_id: str,
    name: str,
    country: str,
    insights: ProcessedInsights,
    source_urls: list[str],
    sections: list = None,
) -> str:
    _ensure_dirs()
    s = get_settings()
    filename = f"{_safe_name(name)}_{content_id[:8]}_keywords.csv"
    filepath = os.path.join(s.CSV_DIR, filename)

    rows = []
    ts = datetime.utcnow().isoformat()

    def row(type_, value, score="", url="", platform=""):
        return {
            "content_id": content_id, "name": name, "country": country,
            "type": type_, "value": value, "trend_score": score,
            "source_url": url, "platform": platform, "refresh_timestamp": ts,
        }

    for i, kw in enumerate(insights.keywords):
        rows.append(row("keyword", kw, score=max(100 - i * 3, 10)))
    for kw in insights.autocomplete_keywords:
        rows.append(row("autocomplete_keyword", kw))
    for term in insights.people_also_search_for:
        rows.append(row("people_also_search_for", term))
    for q in insights.people_also_ask:
        rows.append(row("people_also_ask", q))
    for trend in insights.reddit_trends:
        rows.append(row("reddit_trend", trend))
    for yt in insights.youtube_trends:
        if isinstance(yt, dict):
            rows.append(row("youtube_trend", yt.get("title", ""), url=yt.get("url", ""), platform="youtube"))
        else:
            rows.append(row("youtube_trend", str(yt)))
    for topic in insights.trending_topics:
        rows.append(row("trending_topic", topic, score=90))
    for faq in insights.faqs:
        rows.append(row("faq", faq))
    for trend in insights.market_trends:
        rows.append(row("market_trend", trend))
    # NEW
    for prod in insights.immersive_products:
        if isinstance(prod, dict):
            rows.append(row("immersive_product", prod.get("title", ""),
                           url="", platform=prod.get("source", "")))
    for vid in insights.inline_videos:
        if isinstance(vid, dict):
            rows.append(row("inline_video", vid.get("title", ""),
                           url=vid.get("link", ""), platform=vid.get("platform", "YouTube")))
    for url in source_urls[:20]:
        platform = (
            "youtube"    if "youtube" in url else
            "reddit"     if "reddit" in url else
            "blog_forum" if any(x in url for x in ["quora", "medium"]) else "web"
        )
        rows.append(row("source_url", "", url=url, platform=platform))

    fieldnames = [
        "content_id", "name", "country", "type",
        "value", "trend_score", "source_url", "platform", "refresh_timestamp"
    ]
    def write_csv(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    _safe_write_file(filepath, write_csv)

    logger.info(f"Keywords CSV saved: {filepath}")
    return filepath


def append_refresh_log_csv(content_id: str, name: str, country: str) -> str:
    _ensure_dirs()
    s = get_settings()
    filepath = os.path.join(s.CSV_DIR, "refresh_log.csv")
    fieldnames = ["content_id", "name", "country", "refreshed_at"]
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "content_id": content_id, "name": name,
            "country": country, "refreshed_at": datetime.utcnow().isoformat(),
        })
    return filepath
