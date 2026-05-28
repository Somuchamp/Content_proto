from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    GenerateContentRequest, GeneratedContent, RefreshInterval,
    GenerateFromUrlsRequest, ProcessedInsights, HeadingSection
)
from app.services.aggregator import DataAggregator
from app.services.data_processor import DataProcessor
from app.services.content_generator import ContentGenerator
from app.services.scheduler_service import add_refresh_job
from app.services.url_scraper import GenericUrlScraper
from app.storage.file_storage import (
    save_content_json, load_content_json,
    list_all_content_json, update_content_json,
    save_keywords_csv, append_refresh_log_csv,
    _load_insights,
)
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/content", tags=["Content"])

aggregator  = DataAggregator()
processor   = DataProcessor()
generator   = ContentGenerator()
url_scraper = GenericUrlScraper()


def _interval_to_hours(interval: RefreshInterval, custom_hours: int | None) -> int:
    return {
        RefreshInterval.daily:   24,
        RefreshInterval.weekly:  168,
        RefreshInterval.monthly: 720,
        RefreshInterval.custom:  custom_hours or 24,
    }.get(interval, 168)


async def _run_full_pipeline(
    name: str,
    content_type: str,
    country: str,
    max_headings: int,
    refresh_interval: RefreshInterval,
    custom_interval_hours: int | None,
    content_id: str | None = None,
) -> GeneratedContent:

    query = name

    # Step 2: collect data
    raw_data     = await aggregator.gather_all(query, country)
    context_text = aggregator.build_context_text(raw_data["items"])

    # Step 3: process insights
    insights = processor.process(
        name           = name,
        content_type   = content_type,
        country        = country,
        context        = context_text,
        all_items      = raw_data["items"],
        serp_related   = raw_data.get("serp_related_searches", []),
        serp_paa       = raw_data.get("people_also_ask", []),
        serp_pas       = raw_data.get("people_also_search_for", []),
        autocomplete   = raw_data.get("autocomplete", []),
    )

    # Attach SERP rich features directly (not LLM-generated)
    insights.immersive_products     = raw_data.get("immersive_products", [])
    insights.more_products          = raw_data.get("more_products", [])
    insights.inline_videos          = raw_data.get("inline_videos", [])
    insights.more_videos            = raw_data.get("more_videos", [])
    insights.refine_searches        = raw_data.get("refine_searches", [])
    insights.ai_overview_text       = raw_data.get("ai_overview_text", [])
    insights.ai_overview_references = raw_data.get("ai_overview_references", [])

    # Steps 4+5: generate content sections
    sections = generator.generate(
        name         = name,
        content_type = content_type,
        country      = country,
        insights     = insights,
        context      = context_text,
        max_headings = max_headings,
    )

    cid = content_id or str(uuid.uuid4())
    now = datetime.utcnow()
    hrs = _interval_to_hours(refresh_interval, custom_interval_hours)

    content = GeneratedContent(
        id                    = cid,
        name                  = name,
        content_type          = content_type,
        country               = country,
        sections              = sections,
        insights              = insights,
        sources_used          = raw_data["sources_used"],
        source_urls           = raw_data["source_urls"],
        created_at            = now,
        refresh_interval      = refresh_interval,
        custom_interval_hours = custom_interval_hours,
        next_refresh_at       = now + timedelta(hours=hrs),
    )

    if content_id:
        update_content_json(content)
        append_refresh_log_csv(cid, name, country)
    else:
        save_content_json(content)

    save_keywords_csv(cid, name, country, insights, raw_data["source_urls"])
    return content


@router.post("/generate", response_model=GeneratedContent, status_code=201)
async def generate_content(req: GenerateContentRequest):
    content = await _run_full_pipeline(
        name                  = req.name,
        content_type          = req.content_type.value,
        country               = req.country,
        max_headings          = req.max_headings,
        refresh_interval      = req.refresh_interval,
        custom_interval_hours = req.custom_interval_hours,
    )

    async def refresh_job(cid: str):
        record = load_content_json(cid)
        if record:
            await _run_full_pipeline(
                name                  = record["name"],
                content_type          = record["content_type"],
                country               = record["country"],
                max_headings          = record.get("metadata", {}).get("total_headings", 7),
                refresh_interval      = RefreshInterval(record["refresh_interval"]),
                custom_interval_hours = record.get("custom_interval_hours"),
                content_id            = cid,
            )

    add_refresh_job(
        content_id   = content.id,
        interval     = req.refresh_interval,
        custom_hours = req.custom_interval_hours,
        refresh_fn   = refresh_job,
    )
    return content


@router.post("/generate-from-urls", response_model=GeneratedContent, status_code=201)
async def generate_from_urls(req: GenerateFromUrlsRequest):
    scraped_texts = await url_scraper.scrape_urls_concurrently(req.urls)
    if not scraped_texts:
        raise HTTPException(status_code=400, detail="Failed to extract text from URLs.")

    context_text = "\n\n---\n\n".join(scraped_texts)[:20000]

    insights = processor.process(
        name         = req.name,
        content_type = req.content_type.value,
        country      = req.country,
        context      = context_text,
        all_items    = [],
        serp_related = [],
        serp_paa     = [],
        serp_pas     = [],
        autocomplete = [],
    )

    sections = generator.generate(
        name         = req.name,
        content_type = req.content_type.value,
        country      = req.country,
        insights     = insights,
        context      = context_text,
        max_headings = req.max_headings,
    )

    cid = str(uuid.uuid4())
    now = datetime.utcnow()

    content = GeneratedContent(
        id                    = cid,
        name                  = req.name,
        content_type          = req.content_type.value,
        country               = req.country,
        sections              = sections,
        insights              = insights,
        sources_used          = ["url_scraper"],
        source_urls           = req.urls,
        created_at            = now,
        refresh_interval      = RefreshInterval("custom"),
        custom_interval_hours = 24,
        next_refresh_at       = None,
    )

    save_content_json(content)
    save_keywords_csv(cid, req.name, req.country, insights, req.urls)
    return content


@router.get("/{content_id}", response_model=GeneratedContent)
async def get_content(content_id: str):
    record = load_content_json(content_id)
    if not record:
        raise HTTPException(status_code=404, detail="Content not found")

    saved = record.get("insights", {})
    loaded = _load_insights(saved)

    return GeneratedContent(
        id             = record["id"],
        name           = record["name"],
        content_type   = record["content_type"],
        country        = record["country"],
        sections       = [HeadingSection(**s) for s in record["sections"]],
        insights       = ProcessedInsights(**loaded),
        sources_used   = record.get("sources_used", []),
        source_urls    = record.get("source_urls", []),
        created_at     = datetime.fromisoformat(record["created_at"]),
        refresh_interval      = record["refresh_interval"],
        custom_interval_hours = record.get("custom_interval_hours"),
        next_refresh_at       = datetime.fromisoformat(record["next_refresh_at"])
                                if record.get("next_refresh_at") else None,
    )


@router.get("/", response_model=list[dict])
async def list_content():
    return list_all_content_json()