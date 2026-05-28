from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class ContentType(str, Enum):
    category = "category"
    brand    = "brand"
    keyword  = "keyword"        # NEW: generates blog-structured content


class RefreshInterval(str, Enum):
    daily   = "daily"
    weekly  = "weekly"
    monthly = "monthly"
    custom  = "custom"


# ── Step 1: User Input ────────────────────────────────────────────────────────
class GenerateContentRequest(BaseModel):
    name: str = Field(..., example="Wireless Earbuds")
    content_type: ContentType = ContentType.category
    country: str = Field(..., example="United States")
    max_headings: int = Field(default=7, ge=1, le=20)
    refresh_interval: RefreshInterval = RefreshInterval.weekly
    custom_interval_hours: Optional[int] = Field(
        default=None,
        description="Used only when refresh_interval is 'custom'. Value in hours."
    )


class GenerateFromUrlsRequest(BaseModel):
    urls: List[str] = Field(..., max_items=200)
    name: str = Field(..., example="Wireless Earbuds")
    content_type: ContentType = ContentType.category
    country: str = Field(..., example="United States")
    max_headings: int = Field(default=7, ge=1, le=20)


# ── Intermediate: Processed Data ──────────────────────────────────────────────
class ScrapedItem(BaseModel):
    source: str
    title: str
    description: str
    url: str


# NEW: Immersive product (Google Shopping grid item)
class ImmersiveProduct(BaseModel):
    category:        str  = ""
    thumbnail:       str  = ""
    source:          str  = ""
    title:           str  = ""
    rating:          Optional[float] = None
    reviews:         Optional[int]   = None
    price:           str  = ""
    extracted_price: Optional[float] = None


# NEW: Inline video from SERP
class InlineVideo(BaseModel):
    position:  int  = 0
    title:     str  = ""
    link:      str  = ""
    thumbnail: str  = ""
    channel:   str  = ""
    platform:  str  = ""


# NEW: AI Overview reference
class AIOverviewReference(BaseModel):
    title:   str = ""
    link:    str = ""
    snippet: str = ""
    source:  str = ""
    index:   int = 0


class ProcessedInsights(BaseModel):
    keywords:               List[str]       = []
    autocomplete_keywords:  List[str]       = []
    keyword_clusters:       List[List[str]] = []
    keyword_difficulty:     Dict[str, int]  = {}

    reddit_trends:          List[str]       = []
    youtube_trends:         List[Any]       = []   # list of {title, url}

    people_also_ask:        List[str]       = []
    people_also_search_for: List[str]       = []

    trending_topics:        List[str]       = []
    faqs:                   List[str]       = []
    market_trends:          List[str]       = []

    # NEW: SERP rich features
    immersive_products:     List[Any]       = []   # Popular products grid
    more_products:          List[Any]       = []   # "More products" (shown on button)
    inline_videos:          List[Any]       = []   # Inline video results (top 3)
    more_videos:            List[Any]       = []   # More video content (on button)
    refine_searches:        List[Any]       = []   # {query, link} refine_this_search chips
    ai_overview_text:       List[str]       = []   # plain text blocks from AI overview
    ai_overview_references: List[Any]       = []   # AIOverviewReference dicts


# ── Step 5: Content Heading Section ──────────────────────────────────────────
class HeadingSection(BaseModel):
    heading: str
    body:    str


# ── Final Output ──────────────────────────────────────────────────────────────
class GeneratedContent(BaseModel):
    id:                   str
    name:                 str
    content_type:         ContentType
    country:              str
    sections:             List[HeadingSection]
    insights:             ProcessedInsights
    sources_used:         List[str]
    source_urls:          List[str]
    created_at:           datetime
    refresh_interval:     RefreshInterval
    custom_interval_hours: Optional[int]   = None
    next_refresh_at:      Optional[datetime] = None


# ── Scheduler ─────────────────────────────────────────────────────────────────
class SchedulerRequest(BaseModel):
    content_id:           str
    refresh_interval:     RefreshInterval
    custom_interval_hours: Optional[int] = None


class SchedulerResponse(BaseModel):
    job_id:      str
    content_id:  str
    next_run_at: datetime
    message:     str