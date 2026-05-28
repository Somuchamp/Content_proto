---
title: Content Studio AI
emoji: ✨
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8501
pinned: false
---

# E-Commerce Content Generation Tool

Automatically generates **SEO-optimized, heading-based content** for category and brand pages by:
1. Collecting data from YouTube, Google SERP, Reddit, and Blog/Forums
2. Extracting keywords, FAQs, and market trends via AI
3. Generating structured content under logical headings
4. Storing everything in **CSV + JSON files** (no database)
5. Auto-refreshing content on a user-defined schedule

---

## 🚀 Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env and fill in your keys

# 3. Run the server
uvicorn app.main:app --reload

# Swagger docs at:
http://localhost:8000/docs
```

---

## 📡 API Usage

### Generate Content
```http
POST /api/content/generate
{
  "name": "Wireless Earbuds",
  "content_type": "category",
  "country": "United States",
  "max_headings": 7,
  "refresh_interval": "weekly"
}
```

### Get Content by ID
```http
GET /api/content/{content_id}
```

### List All Content
```http
GET /api/content/
```

### Set/Update Refresh Schedule
```http
POST /api/scheduler/set
{
  "content_id": "abc123",
  "refresh_interval": "daily"
}
```

### Cancel Schedule
```http
DELETE /api/scheduler/cancel/{content_id}
```

---

## 📁 Data Storage

### JSON Files (`data/json/`)
Each content item gets its own JSON file containing:
- Generated headings and body content
- Source references and metadata
- Refresh schedule info

### CSV Files (`data/csv/`)
- `{name}_keywords.csv` — extracted keywords, URLs, platform types, trend scores
- `refresh_log.csv` — log of all refresh cycles with timestamps

---

## 🔑 Required API Keys

| Key | Source |
|-----|--------|
| `YOUTUBE_API_KEY` | console.cloud.google.com → YouTube Data API v3 |
| `SERP_API_KEY` | serpapi.com |
| `REDDIT_CLIENT_ID` | reddit.com/prefs/apps |
| `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps |
| `ANTHROPIC_API_KEY` | console.anthropic.com |

---

## 🗂 Project Structure

```
app/
├── main.py                          # FastAPI entry point
├── config.py                        # Settings from .env
├── models/schemas.py                # Pydantic models
├── scrapers/
│   ├── youtube_scraper.py           # YouTube Data API
│   ├── serp_scraper.py              # Google SERP (SerpAPI)
│   ├── reddit_scraper.py            # Reddit PRAW
│   └── blog_forum_scraper.py        # Blog & forum scraper
├── services/
│   ├── aggregator.py                # Concurrent scraper runner
│   ├── data_processor.py            # Keyword/FAQ/trend extraction
│   ├── content_generator.py         # AI heading + content generation
│   └── scheduler_service.py         # APScheduler (daily/weekly/monthly)
├── storage/
│   └── file_storage.py              # CSV + JSON read/write (no DB)
└── api/routes/
    ├── content.py                   # /api/content endpoints
    └── scheduler.py                 # /api/scheduler endpoints
```