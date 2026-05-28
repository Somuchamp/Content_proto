import cloudscraper
from bs4 import BeautifulSoup
import logging
import asyncio

logger = logging.getLogger(__name__)

class GenericUrlScraper:
    """
    Scrapes arbitrary URLs to extract main text content.
    Uses cloudscraper to bypass common bot protections.
    """
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    def scrape_url(self, url: str) -> str:
        """Fetch and extract text from a single URL."""
        try:
            logger.info(f"Scraping URL: {url}")
            # Use a slightly longer timeout for unknown sites
            resp = self.scraper.get(url, timeout=20)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.extract()

            # Extract text from paragraphs and headers
            tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li'])
            
            text_chunks = []
            for tag in tags:
                text = tag.get_text(strip=True)
                if text:
                    text_chunks.append(text)

            content = " ".join(text_chunks)
            
            # Simple heuristic to ensure we got something meaningful
            if len(content) < 50:
                logger.warning(f"Very little content extracted from {url}. Might be blocked or JS-rendered.")
                return ""

            return content
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return ""

    async def scrape_urls_concurrently(self, urls: list[str]) -> list[str]:
        """Scrape a list of URLs concurrently."""
        # cloudscraper isn't inherently async, so we wrap it in asyncio.to_thread
        tasks = [asyncio.to_thread(self.scrape_url, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Concurrent scrape task failed: {res}")
            elif res:
                 valid_results.append(res)
                 
        return valid_results
