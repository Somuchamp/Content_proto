import os
import json
import base64
import httpx
from typing import Dict, Any, List, Optional
import logging
import sys
from dotenv import load_dotenv

# Prevent Windows console encoding issues with emojis
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv()

logger = logging.getLogger(__name__)

# Full country list (same as Studio Pipeline / serp_scraper.COUNTRY_DATA)
from app.services.country_registry import COUNTRY_CODES, COUNTRY_LANGUAGES, SUPPORTED_COUNTRIES

# Ensure to map country names to standard dataforseo loc names/codes if required, but DataForSEO often accepts standard ISOs or loc IDs.
# For simplicity, we use country names as location_name in DataForSEO API

def clean_domain(url: str) -> str:
    """Extract domain from a given URL/string, stripping protocols, www, and paths."""
    url = url.strip()
    if not url:
        return ""
    import urllib.parse
    if not url.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse("https://" + url)
    else:
        parsed = urllib.parse.urlparse(url)
    domain = parsed.hostname or url
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

ADULT_KEYWORDS_BLACK_CHIPS = {
    # Adult content / pornography
    "sex", "porn", "xxnx", "xnxx", "xvideos", "xhamster", "xvideo", "xxx", "adult", "nude", 
    "naked", "erotic", "hentai", "sensual", "bdsm", "fetish", "milf", "porno", "sexo", "puta",
    "escort", "prostitute", "camgirl", "onlyfans", "slut", "bitch", "bastard", "fuck", "ass", 
    "dick", "pussy", "vagina", "penis", "breast", "boob", "vibrator", "dildo", "xmaster", "vulgar",
    
    # Gambling / illegal betting / lottery
    "satta", "matka", "sattamatka", "satamataka", "casino", "betting", "gambling", "lottery",
    "jackpot", "rulet", "roulette", "poker", "baccarat"
}

def is_adult_or_inappropriate(keyword: str) -> bool:
    if not keyword:
        return False
    kw_lower = keyword.lower().strip()
    for term in ADULT_KEYWORDS_BLACK_CHIPS:
        if term in kw_lower:
            return True
    return False

LANGUAGE_NAME_TO_CODE = {
    "English": "en", "German": "de", "French": "fr", "Spanish": "es", "Italian": "it",
    "Portuguese": "pt", "Dutch": "nl", "Polish": "pl", "Russian": "ru", "Ukrainian": "uk",
    "Japanese": "ja", "Korean": "ko", "Chinese": "zh", "Thai": "th", "Vietnamese": "vi",
    "Indonesian": "id", "Malay": "ms", "Turkish": "tr", "Greek": "el", "Romanian": "ro",
    "Hungarian": "hu", "Czech": "cs", "Slovak": "sk", "Bulgarian": "bg", "Croatian": "hr",
    "Serbian": "sr", "Slovenian": "sl", "Swedish": "sv", "Norwegian": "no", "Danish": "da",
    "Finnish": "fi", "Icelandic": "is", "Hebrew": "he", "Arabic": "ar", "Persian": "fa",
    "Bengali": "bn", "Sinhala": "si", "Nepali": "ne", "Khmer": "km", "Lao": "lo",
    "Burmese": "my", "Uzbek": "uz", "Georgian": "ka", "Armenian": "hy", "Azerbaijani": "az",
    "Amharic": "am", "Swahili": "sw", "Kinyarwanda": "rw"
}

class DataForSeoClient:
    BASE_URL = "https://api.dataforseo.com/v3/"

    def __init__(self):
        api_key = os.getenv("DATAFORSEO_API_KEY")
        login = os.getenv("DATAFORSEO_LOGIN")
        password = os.getenv("DATAFORSEO_PASSWORD")
        
        if api_key:
            self.auth_header = f"Basic {api_key}"
        elif login and password:
            credentials = f"{login}:{password}"
            self.auth_header = f"Basic {base64.b64encode(credentials.encode('utf-8')).decode('utf-8')}"
        else:
            logger.warning("DataForSEO credentials not fully set in environment variables.")
            self.auth_header = ""
        
        self.headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }

    def _post(self, endpoint: str, data: list) -> Optional[Dict[str, Any]]:
        try:
            print(f"📡 DataForSEO Request [POST]: {endpoint} | Payload: {json.dumps(data)}")
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self.headers,
                    json=data
                )
                response.raise_for_status()
                res_data = response.json()
                
                # Check for unsupported location self-healing
                if res_data.get("tasks"):
                    task = res_data["tasks"][0]
                    if task.get("status_code") == 40501 and "location_name" in task.get("status_message", ""):
                        print("⚠️ Unsupported country detected by DataForSEO Labs. Automatically self-healing and retrying with 'United States' fallback...")
                        fallback_data = []
                        for item in data:
                            new_item = dict(item)
                            if "location_name" in new_item:
                                new_item["location_name"] = "United States"
                            if "language_name" in new_item:
                                new_item["language_name"] = "English"
                            fallback_data.append(new_item)
                        return self._post(endpoint, fallback_data)
                
                print(f"✅ DataForSEO Response [POST]: {endpoint} | Status: {res_data.get('tasks', [{}])[0].get('status_message', 'Unknown')}")
                return res_data
        except Exception as e:
            print(f"❌ DataForSEO API error on {endpoint}: {e}")
            logger.error(f"DataForSEO API error on {endpoint}: {e}")
            return {"error": str(e)}

    def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        try:
            print(f"📡 DataForSEO Request [GET]: {endpoint}")
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self.headers
                )
                response.raise_for_status()
                res_data = response.json()
                print(f"✅ DataForSEO Response [GET]: {endpoint} | Status: {res_data.get('tasks', [{}])[0].get('status_message', 'Unknown')}")
                return res_data
        except Exception as e:
            print(f"❌ DataForSEO GET API error on {endpoint}: {e}")
            logger.error(f"DataForSEO GET API error on {endpoint}: {e}")
            return {"error": str(e)}

    # ==========================================
    # 1. Keyword Research Module
    # ==========================================
    
    def keyword_overview(self, keyword: str, country: str = "United States") -> Dict[str, Any]:
        """Fetch search volume, CPC, Competition for a keyword."""
        data = [{
            "keywords": [keyword],
            "location_name": country,
            "language_name": COUNTRY_LANGUAGES.get(country, "English")
        }]
        res = self._post("dataforseo_labs/google/historical_search_volume/live", data)
        payload = self._first_task_payload(res)
        if payload and payload.get("items"):
            first_item = payload["items"][0]
            if isinstance(first_item, dict):
                k_data = first_item.get("keyword_info", {})
                k_props = first_item.get("keyword_properties", {})
                return {
                    "volume": k_data.get("search_volume", 0),
                    "cpc": k_data.get("cpc", 0),
                    "competition": k_data.get("competition", 0),
                    "difficulty": k_props.get("keyword_difficulty", 0),
                    "clicks": 0, # Placeholder or estimate if not explicitly provided
                    "global_volume": k_data.get("search_volume", 0),
                    "clicks_per_search": 0
                }
        return {"error": "No data found for keyword overview."}

    def keyword_ideas(self, keyword: str, country: str = "United States", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch keyword suggestions & related keywords."""
        data = [{
            "keywords": [keyword],
            "location_name": country,
            "language_name": COUNTRY_LANGUAGES.get(country, "English"),
            "limit": limit
        }]
        res = self._post("dataforseo_labs/google/keyword_ideas/live", data)
        return self._parse_keyword_list(res)

    def _first_task_payload(self, res: Optional[dict]) -> Optional[Dict[str, Any]]:
        """Safely read the first result object from a DataForSEO task response."""
        if not res or "tasks" not in res or not res["tasks"]:
            return None
        task = res["tasks"][0]
        if task.get("status_code") and task.get("status_code") != 20000:
            logger.warning(
                "DataForSEO task error %s: %s",
                task.get("status_code"),
                task.get("status_message", ""),
            )
            return None
        result_list = task.get("result")
        if not result_list or not isinstance(result_list, list):
            return None
        first = result_list[0]
        return first if isinstance(first, dict) else None

    def keyword_search_suggestions(self, keyword: str, country: str = "United States", limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch search suggestions / long-tail expansion using Live Autocomplete SERP."""
        lang_name = COUNTRY_LANGUAGES.get(country, "English")
        lang_code = LANGUAGE_NAME_TO_CODE.get(lang_name, "en")
        data = [{
            "keyword": keyword,
            "location_name": country,
            "language_code": lang_code
        }]
        res = self._post("serp/google/autocomplete/live/advanced", data)
        out = []
        payload = self._first_task_payload(res)
        if payload:
            items = payload.get("items") or []
            for item in items[:limit]:
                kw = item.get("suggestion", "")
                if kw:
                    if is_adult_or_inappropriate(kw):
                        continue
                    out.append({
                        "keyword": kw,
                        "volume": 0,
                        "difficulty": 0,
                        "cpc": 0,
                        "competition": 0,
                        "clicks": "—"
                    })
        return out

    def keyword_also_rank_for(self, keyword: str, country: str = "United States", limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch 'also rank for' style keywords using Google Related Keywords endpoint."""
        data = [{
            "keyword": keyword,
            "location_name": country,
            "language_name": COUNTRY_LANGUAGES.get(country, "English"),
            "limit": limit
        }]
        res = self._post("dataforseo_labs/google/related_keywords/live", data)
        return self._parse_keyword_list(res)

    def _parse_keyword_list(self, res: dict) -> List[Dict[str, Any]]:
        out = []
        payload = self._first_task_payload(res)
        if payload and payload.get("items"):
            for item in payload["items"]:
                if not isinstance(item, dict):
                    continue
                kw_data = item.get("keyword_data", {})
                if not kw_data and "keyword_info" in item:
                    kw_data = item
                kw_info = kw_data.get("keyword_info", {})
                kw_props = kw_data.get("keyword_properties", {})
                kw = kw_data.get("keyword") or item.get("keyword", "")
                if kw:
                    if is_adult_or_inappropriate(kw):
                        continue
                    out.append({
                        "keyword": kw,
                        "volume": kw_info.get("search_volume", 0),
                        "difficulty": kw_props.get("keyword_difficulty", 0),
                        "cpc": kw_info.get("cpc", 0),
                        "competition": kw_info.get("competition", 0),
                        "clicks": "—",
                    })
        return out

    # ==========================================
    # 2. SERP Analysis Module
    # ==========================================
    
    def serp_analysis(self, keyword: str, country: str = "United States") -> Dict[str, Any]:
        """Fetch advanced SERP data including featured snippets, PAA, Ads."""
        data = [{
            "keyword": keyword,
            "location_name": country,
            "language_name": COUNTRY_LANGUAGES.get(country, "English"),
            "device": "desktop",
            "os": "windows"
        }]
        res = self._post("serp/google/organic/live/advanced", data)
        out = {
            "organic": [],
            "featured_snippet": None,
            "people_also_ask": [],
            "ads": [],
            "images": []
        }
        if res and "tasks" in res and res["tasks"] and "result" in res["tasks"][0]:
            result_data = res["tasks"][0]["result"]
            if result_data and len(result_data) > 0:
                items = result_data[0].get("items") or []
                for item in items:
                    i_type = item.get("type")
                    if i_type == "organic":
                        out["organic"].append({
                            "rank": item.get("rank_group"),
                            "url": item.get("url"),
                            "title": item.get("title"),
                            "domain": item.get("domain"),
                            "snippet": item.get("description")
                        })
                    elif i_type == "featured_snippet":
                        out["featured_snippet"] = {
                            "url": item.get("url"),
                            "title": item.get("title"),
                            "description": item.get("description")
                        }
                    elif i_type == "people_also_ask":
                        for paa in item.get("items", []):
                            out["people_also_ask"].append(paa.get("title"))
                    elif i_type == "paid":
                        out["ads"].append({
                            "url": item.get("url"),
                            "title": item.get("title"),
                            "description": item.get("description")
                        })
                    elif i_type == "images":
                        for img in item.get("items", []):
                            out["images"].append(img.get("url"))
        return out

    # ==========================================
    # 3. Competitor Analysis
    # ==========================================

    def competitor_overview_batch(self, urls: List[str], country: str = "United States") -> List[Dict[str, Any]]:
        """Overview for multiple domains using active DataForSEO Labs metrics."""
        data = []
        skipped = []
        for url in urls:
            cleaned_target = clean_domain(url)
            if not cleaned_target or "." not in cleaned_target:
                skipped.append(url)
                continue
            data.append({
                "target": cleaned_target,
                "location_name": country,
                "language_name": COUNTRY_LANGUAGES.get(country, "English")
            })

        if not data:
            return [{"url": u, "error": "Invalid domain format"} for u in skipped] or [{"error": "No valid competitor domains"}]

        # Fetch Traffic & Keywords from DataForSEO Labs
        res = self._post("dataforseo_labs/google/domain_rank_overview/live", data)

        out = []
        if res and "tasks" in res:
            for task in res["tasks"]:
                target = task.get("data", {}).get("target", "")
                status_code = task.get("status_code")
                status_msg = task.get("status_message", "")
                if status_code and status_code != 20000:
                    out.append({"url": target, "error": f"DataForSEO task error {status_code}: {status_msg}"})
                    continue
                if task.get("result") and task["result"]:
                    result_obj = task["result"][0]
                    items = result_obj.get("items") or []
                    metrics = {}
                    if items:
                        metrics = items[0].get("metrics", {}).get("organic", {})
                    else:
                        metrics = result_obj.get("metrics", {}).get("organic", {})
                        
                    out.append({
                        "url": target,
                        "domain_rating": "—",
                        "organic_traffic": metrics.get("etv", 0),
                        "organic_keywords": metrics.get("count", 0),
                        "backlinks": "—",
                        "referring_domains": "—",
                    })
                else:
                    out.append({"url": target, "error": "No data"})
        elif res and res.get("error"):
            out.append({"url": "", "error": f"DataForSEO API error: {res.get('error')}"})

        for u in skipped:
            out.append({"url": u, "error": "Invalid domain format"})
        return out
        
    # ==========================================
    # 4. Backlink Analysis (Subscription Inactive)
    # ==========================================

    def site_explorer_overview(self, target: str, country: str = "United States") -> Dict[str, Any]:
        """Fetch organic overview from DataForSEO Labs."""
        res_rank = self.competitor_overview_batch([target], country)
        traffic = 0
        org_kw = 0
        if res_rank and "error" not in res_rank[0]:
            traffic = res_rank[0].get("organic_traffic", 0)
            org_kw = res_rank[0].get("organic_keywords", 0)

        return {
            "domain_rating": "—",
            "org_traffic": traffic,
            "backlinks": "—",
            "referring_domains": "—",
            "org_keywords": org_kw
        }

    def site_explorer_backlinks(self, target: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Inactive due to backlinks subscription limit."""
        return []

    def site_explorer_anchors(self, target: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Inactive due to backlinks subscription limit."""
        return []

    def site_explorer_top_pages(self, target: str, country: str = "United States", limit: int = 20) -> List[Dict[str, Any]]:
        """Inactive due to backlinks subscription limit."""
        return []

    def site_explorer_organic_keywords(self, target: str, country: str = "United States", limit: int = 50, filters: Optional[list] = None) -> List[Dict[str, Any]]:
        cleaned_target = clean_domain(target)
        payload = {
            "target": cleaned_target,
            "location_name": country,
            "language_name": COUNTRY_LANGUAGES.get(country, "English"),
            "limit": limit,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"]
        }
        if filters:
            payload["filters"] = filters
            
        data = [payload]
        res = self._post("dataforseo_labs/google/ranked_keywords/live", data)
        out = []
        if res and "tasks" in res and res["tasks"] and "result" in res["tasks"][0]:
            result_data = res["tasks"][0]["result"]
            if result_data and len(result_data) > 0:
                items = result_data[0].get("items") or []
                for item in items:
                    kw_data = item.get("keyword_data", {})
                    kw_info = kw_data.get("keyword_info", {})
                    ranked = item.get("ranked_serp_element", {})
                    serp_item = ranked.get("serp_item", {}) or {}
                    etv = serp_item.get("etv", "—")
                    kw = kw_data.get("keyword", "")
                    if kw:
                        if is_adult_or_inappropriate(kw):
                            continue
                        out.append({
                            "keyword": kw,
                            "position": serp_item.get("rank_absolute", "—"),
                            "traffic": etv,
                            "volume": kw_info.get("search_volume", 0),
                            "difficulty": kw_info.get("seo_difficulty", 0),
                            "cpc": kw_info.get("cpc", 0)
                        })
        return out

    def rank_tracker_positions(self, target: str, country: str, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        filters = []
        if keywords:
            kw_lowers = [k.lower().strip() for k in keywords if k.strip()]
            for i, kw in enumerate(kw_lowers):
                if i > 0:
                    filters.append("or")
                filters.append(["keyword_data.keyword", "like", f"%{kw}%"])
        
        # If filters is populated, it will push filtering to the API
        return self.site_explorer_organic_keywords(target, country, limit=limit, filters=filters if filters else None)

    # ==========================================
    # 5. Content Insights
    # ==========================================

    def content_explorer(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        data = [{
            "keyword": keyword,
            "location_name": "United States",
            "language_name": "English",
            "limit": limit
        }]
        res = self._post("serp/google/organic/live/advanced", data)
        out = []
        if res and "tasks" in res and res["tasks"]:
            task = res["tasks"][0]
            if task.get("result") and len(task["result"]) > 0:
                items = task["result"][0].get("items") or []
                for item in items:
                    if item.get("type") == "organic":
                        out.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "domain": item.get("domain", ""),
                            "traffic": "—",
                            "referring_domains": "—",
                            "facebook_shares": "—",
                            "twitter_shares": "—",
                            "words": "—"
                        })
        return out

    # ==========================================
    # 6. Site Audit
    # ==========================================
    def site_audit_start(self, url: str) -> str:
        data = [{"target": url, "max_crawl_pages": 50}]
        res = self._post("on_page/task_post", data)
        if res and "tasks" in res and res["tasks"]:
            return res["tasks"][0].get("id", "")
        return ""

    def site_audit_status(self, task_id: str) -> Dict[str, Any]:
        res = self._get(f"on_page/summary/{task_id}")
        if res and "tasks" in res and res["tasks"]:
            task = res["tasks"][0]
            status = task.get("status_message", "")
            if task.get("result") and task["result"]:
                r = task["result"][0]
                if isinstance(r, dict):
                    pi = r.get("page_metrics", {})
                    if not isinstance(pi, dict):
                        pi = {}
                    
                    checks = pi.get("checks", {})
                    if not isinstance(checks, dict):
                        checks = {}
                    
                    def safe_val(v):
                        try:
                            return int(v) if v is not None else 0
                        except Exception:
                            return 0
                    
                    # Calculate errors from key metric issues
                    errors = (
                        safe_val(pi.get("broken_links")) +
                        safe_val(pi.get("broken_resources")) +
                        safe_val(pi.get("duplicate_title")) +
                        safe_val(pi.get("duplicate_content")) +
                        safe_val(checks.get("is_http")) +
                        safe_val(checks.get("is_broken")) +
                        safe_val(checks.get("is_4xx_code")) +
                        safe_val(checks.get("is_5xx_code")) +
                        safe_val(checks.get("no_title")) +
                        safe_val(checks.get("duplicate_title_tag")) +
                        safe_val(checks.get("fatal")) +
                        safe_val(checks.get("error"))
                    )
                    
                    # Calculate warnings from secondary issues
                    warnings = (
                        safe_val(checks.get("warning")) +
                        safe_val(checks.get("no_description")) +
                        safe_val(checks.get("no_h1_tag")) +
                        safe_val(checks.get("title_too_short")) +
                        safe_val(checks.get("title_too_long")) +
                        safe_val(checks.get("no_favicon")) +
                        safe_val(checks.get("low_content_rate")) +
                        safe_val(checks.get("low_character_count")) +
                        safe_val(checks.get("low_readability_rate")) +
                        safe_val(checks.get("has_render_blocking_resources")) +
                        safe_val(checks.get("no_image_alt"))
                    )
                    
                    domain_info = r.get("domain_info", {})
                    if not isinstance(domain_info, dict):
                        domain_info = {}
                    
                    # Try to fetch score from page_metrics first, then fall back to domain_info
                    health = pi.get("onpage_score", 0)
                    if not health:
                        health = domain_info.get("onpage_score", 0)
                    
                    crawl_status = r.get("crawl_status", {})
                    if not isinstance(crawl_status, dict):
                        crawl_status = {}
                    crawled_pages = crawl_status.get("pages_crawled", 0)
                    
                    progress = r.get("crawl_progress", "Crawling...")
                    
                    return {
                        "status": status,
                        "health_score": health,
                        "errors": errors,
                        "warnings": warnings,
                        "crawled_pages": crawled_pages,
                        "progress": progress
                    }
            return {"status": status, "progress": "Crawling..."}
        return {"status": "Error"}

    # ==========================================
    # 7. LLM Mentions API
    # ==========================================
    def llm_mentions_search(self, target: str, platform: str = "chat_gpt", country: str = "United States", limit: int = 20) -> List[Dict[str, Any]]:
        data = [{
            "location_name": country,
            "language_name": "English",
            "platform": platform,
            "target": [{"keyword": target, "search_scope": ["answer"]}],
            "limit": limit
        }]
        res = self._post("ai_optimization/llm_mentions/search/live", data)
        out = []
        if res and "tasks" in res and res["tasks"]:
            task = res["tasks"][0]
            if task.get("result") and len(task["result"]) > 0:
                items = task["result"][0].get("items") or []
                for item in items:
                    out.append({
                        "platform": item.get("platform", platform),
                        "model": item.get("model_name", "—"),
                        "question": item.get("question", ""),
                        "answer": item.get("answer", ""),
                        "ai_search_volume": item.get("ai_search_volume", 0),
                        "last_response": item.get("last_response_at", "—")
                    })
        return out

# Expose a singleton instance or matching functions to maintain interface
_client = DataForSeoClient()

def keyword_overview(keyword: str, country: str = "United States") -> Dict[str, Any]:
    return _client.keyword_overview(keyword, country)

def keyword_ideas(keyword: str, country: str = "United States", limit: int = 100) -> List[Dict[str, Any]]:
    return _client.keyword_ideas(keyword, country, limit)

def keyword_search_suggestions(keyword: str, country: str = "United States", limit: int = 50) -> List[Dict[str, Any]]:
    return _client.keyword_search_suggestions(keyword, country, limit)

def keyword_also_rank_for(keyword: str, country: str = "United States", limit: int = 50) -> List[Dict[str, Any]]:
    return _client.keyword_also_rank_for(keyword, country, limit)

def rank_tracker_positions(target: str, country: str, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
    return _client.rank_tracker_positions(target, country, keywords, limit)

def content_explorer(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    return _client.content_explorer(keyword, limit)

def site_explorer_overview(target: str, country: str = "United States") -> Dict[str, Any]:
    return _client.site_explorer_overview(target, country)

def site_explorer_backlinks(target: str, limit: int = 30) -> List[Dict[str, Any]]:
    return _client.site_explorer_backlinks(target, limit)

def site_explorer_anchors(target: str, limit: int = 15) -> List[Dict[str, Any]]:
    return _client.site_explorer_anchors(target, limit)

def site_explorer_top_pages(target: str, country: str = "United States", limit: int = 20) -> List[Dict[str, Any]]:
    return _client.site_explorer_top_pages(target, country, limit)

def site_explorer_organic_keywords(target: str, country: str = "United States", limit: int = 50) -> List[Dict[str, Any]]:
    return _client.site_explorer_organic_keywords(target, country, limit)

def site_audit_start(url: str) -> str:
    return _client.site_audit_start(url)

def site_audit_status(task_id: str) -> Dict[str, Any]:
    return _client.site_audit_status(task_id)

def competitor_overview_batch(urls: List[str], country: str = "United States") -> List[Dict[str, Any]]:
    return _client.competitor_overview_batch(urls, country)

def serp_analysis(keyword: str, country: str = "United States") -> Dict[str, Any]:
    return _client.serp_analysis(keyword, country)

def llm_mentions_search(target: str, platform: str = "chat_gpt", country: str = "United States", limit: int = 20) -> List[Dict[str, Any]]:
    return _client.llm_mentions_search(target, platform, country, limit)

def _country_code(country: str) -> str:
    return COUNTRY_CODES.get(country, "US")
