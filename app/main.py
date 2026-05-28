from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import content, scheduler
from app.services.scheduler_service import start_scheduler, stop_scheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("App started.")
    yield
    stop_scheduler()
    logger.info("App stopped.")


app = FastAPI(
    title="E-Commerce Content Generation Tool",
    description=(
        "Automatically generates structured, SEO-optimized content for "
        "category and brand pages by collecting data from YouTube, Google SERP, "
        "Reddit, and blog/forums. Stores output in CSV and JSON files."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(content.router)
app.include_router(scheduler.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# NOTE FOR BACKEND CONTENT SERVICE (content.py / content_service.py):
#
# The SerpScraper.fetch() now returns:
#   {
#     "results":          [...],   # top-10 organic results, page 1 only
#     "related_searches": [...],   # combined related_searches + people_also_search_for
#   }
#
# Your content generation service must map `related_searches` into the saved
# content's `insights` dict under the key "people_also_search_for" so that
# the Streamlit UI can read and display it. Example:
#
#   serp_data = serp_scraper.fetch(query, country)
#   insights["people_also_search_for"] = serp_data.get("related_searches", [])
#
# Without this mapping, the UI tab and banner for "People Also Search For"
# will render empty even though the scraper is collecting the data correctly.
# ---------------------------------------------------------------------------