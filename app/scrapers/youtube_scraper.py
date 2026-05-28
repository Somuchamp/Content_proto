from googleapiclient.discovery import build
from app.config import get_settings
import logging
import datetime

logger = logging.getLogger(__name__)


class YouTubeScraper:
    def __init__(self):
        self.api_key = get_settings().YOUTUBE_API_KEY

    def fetch(self, query: str, country: str, max_results: int = 8) -> list[dict]:
        """
        Fetch YouTube video titles, descriptions for a given query + country.
        """
        if not self.api_key:
            logger.warning("YouTube API key not set. Skipping.")
            return []
            
        last_year = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).isoformat() + "Z"
        
        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)
            request = youtube.search().list(
                q=f"{query} {country} trends OR review",
                part="snippet",
                type="video",
                maxResults=max_results,
                relevanceLanguage="en",
                order="relevance",
                publishedAfter=last_year,
            )
            response = request.execute()
            results = []
            for item in response.get("items", []):
                snippet = item["snippet"]
                video_id = item["id"]["videoId"]
                results.append({
                    "source": "youtube",
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                })
            return results
        except Exception as e:
            logger.error(f"YouTube scrape failed: {e}")
            return []