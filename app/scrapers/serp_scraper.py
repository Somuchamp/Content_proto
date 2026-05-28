import httpx
import re
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
SERPAPI_URL = "https://serpapi.com/search"

COUNTRY_DATA = {
    "saudi":    {"gl": "sa", "location": "Saudi Arabia"},
    "ksa":      {"gl": "sa", "location": "Saudi Arabia"},
    "uae":      {"gl": "ae", "location": "United Arab Emirates"},
    "emirates": {"gl": "ae", "location": "United Arab Emirates"},
    "uk":       {"gl": "gb", "location": "United Kingdom"},
    "us":       {"gl": "us", "location": "United States"},
    "usa":      {"gl": "us", "location": "United States"},
    "america":  {"gl": "us", "location": "United States"},
    "united states":              {"gl": "us", "location": "United States"},
    "united kingdom":             {"gl": "gb", "location": "United Kingdom"},
    "saudi arabia":               {"gl": "sa", "location": "Saudi Arabia"},
    "united arab emirates":       {"gl": "ae", "location": "United Arab Emirates"},
    "afghanistan":                {"gl": "af", "location": "Afghanistan"},
    "albania":                    {"gl": "al", "location": "Albania"},
    "algeria":                    {"gl": "dz", "location": "Algeria"},
    "andorra":                    {"gl": "ad", "location": "Andorra"},
    "angola":                     {"gl": "ao", "location": "Angola"},
    "antigua and barbuda":        {"gl": "ag", "location": "Antigua and Barbuda"},
    "argentina":                  {"gl": "ar", "location": "Argentina"},
    "armenia":                    {"gl": "am", "location": "Armenia"},
    "australia":                  {"gl": "au", "location": "Australia"},
    "austria":                    {"gl": "at", "location": "Austria"},
    "azerbaijan":                 {"gl": "az", "location": "Azerbaijan"},
    "bahamas":                    {"gl": "bs", "location": "Bahamas"},
    "bahrain":                    {"gl": "bh", "location": "Bahrain"},
    "bangladesh":                 {"gl": "bd", "location": "Bangladesh"},
    "barbados":                   {"gl": "bb", "location": "Barbados"},
    "belarus":                    {"gl": "by", "location": "Belarus"},
    "belgium":                    {"gl": "be", "location": "Belgium"},
    "belize":                     {"gl": "bz", "location": "Belize"},
    "benin":                      {"gl": "bj", "location": "Benin"},
    "bhutan":                     {"gl": "bt", "location": "Bhutan"},
    "bolivia":                    {"gl": "bo", "location": "Bolivia"},
    "bosnia and herzegovina":     {"gl": "ba", "location": "Bosnia and Herzegovina"},
    "botswana":                   {"gl": "bw", "location": "Botswana"},
    "brazil":                     {"gl": "br", "location": "Brazil"},
    "brunei":                     {"gl": "bn", "location": "Brunei"},
    "bulgaria":                   {"gl": "bg", "location": "Bulgaria"},
    "burkina faso":               {"gl": "bf", "location": "Burkina Faso"},
    "burundi":                    {"gl": "bi", "location": "Burundi"},
    "cambodia":                   {"gl": "kh", "location": "Cambodia"},
    "cameroon":                   {"gl": "cm", "location": "Cameroon"},
    "canada":                     {"gl": "ca", "location": "Canada"},
    "cape verde":                 {"gl": "cv", "location": "Cape Verde"},
    "central african republic":   {"gl": "cf", "location": "Central African Republic"},
    "chad":                       {"gl": "td", "location": "Chad"},
    "chile":                      {"gl": "cl", "location": "Chile"},
    "china":                      {"gl": "cn", "location": "China"},
    "colombia":                   {"gl": "co", "location": "Colombia"},
    "comoros":                    {"gl": "km", "location": "Comoros"},
    "congo":                      {"gl": "cg", "location": "Congo"},
    "costa rica":                 {"gl": "cr", "location": "Costa Rica"},
    "croatia":                    {"gl": "hr", "location": "Croatia"},
    "cuba":                       {"gl": "cu", "location": "Cuba"},
    "cyprus":                     {"gl": "cy", "location": "Cyprus"},
    "czech republic":             {"gl": "cz", "location": "Czech Republic"},
    "denmark":                    {"gl": "dk", "location": "Denmark"},
    "djibouti":                   {"gl": "dj", "location": "Djibouti"},
    "dominica":                   {"gl": "dm", "location": "Dominica"},
    "dominican republic":         {"gl": "do", "location": "Dominican Republic"},
    "ecuador":                    {"gl": "ec", "location": "Ecuador"},
    "egypt":                      {"gl": "eg", "location": "Egypt"},
    "el salvador":                {"gl": "sv", "location": "El Salvador"},
    "equatorial guinea":          {"gl": "gq", "location": "Equatorial Guinea"},
    "eritrea":                    {"gl": "er", "location": "Eritrea"},
    "estonia":                    {"gl": "ee", "location": "Estonia"},
    "eswatini":                   {"gl": "sz", "location": "Eswatini"},
    "ethiopia":                   {"gl": "et", "location": "Ethiopia"},
    "fiji":                       {"gl": "fj", "location": "Fiji"},
    "finland":                    {"gl": "fi", "location": "Finland"},
    "france":                     {"gl": "fr", "location": "France"},
    "gabon":                      {"gl": "ga", "location": "Gabon"},
    "gambia":                     {"gl": "gm", "location": "Gambia"},
    "georgia":                    {"gl": "ge", "location": "Georgia"},
    "germany":                    {"gl": "de", "location": "Germany"},
    "ghana":                      {"gl": "gh", "location": "Ghana"},
    "greece":                     {"gl": "gr", "location": "Greece"},
    "grenada":                    {"gl": "gd", "location": "Grenada"},
    "guatemala":                  {"gl": "gt", "location": "Guatemala"},
    "guinea":                     {"gl": "gn", "location": "Guinea"},
    "guinea-bissau":              {"gl": "gw", "location": "Guinea-Bissau"},
    "guyana":                     {"gl": "gy", "location": "Guyana"},
    "haiti":                      {"gl": "ht", "location": "Haiti"},
    "honduras":                   {"gl": "hn", "location": "Honduras"},
    "hungary":                    {"gl": "hu", "location": "Hungary"},
    "iceland":                    {"gl": "is", "location": "Iceland"},
    "india":                      {"gl": "in", "location": "India"},
    "indonesia":                  {"gl": "id", "location": "Indonesia"},
    "iran":                       {"gl": "ir", "location": "Iran"},
    "iraq":                       {"gl": "iq", "location": "Iraq"},
    "ireland":                    {"gl": "ie", "location": "Ireland"},
    "israel":                     {"gl": "il", "location": "Israel"},
    "italy":                      {"gl": "it", "location": "Italy"},
    "jamaica":                    {"gl": "jm", "location": "Jamaica"},
    "japan":                      {"gl": "jp", "location": "Japan"},
    "jordan":                     {"gl": "jo", "location": "Jordan"},
    "kazakhstan":                 {"gl": "kz", "location": "Kazakhstan"},
    "kenya":                      {"gl": "ke", "location": "Kenya"},
    "kiribati":                   {"gl": "ki", "location": "Kiribati"},
    "kuwait":                     {"gl": "kw", "location": "Kuwait"},
    "kyrgyzstan":                 {"gl": "kg", "location": "Kyrgyzstan"},
    "laos":                       {"gl": "la", "location": "Laos"},
    "latvia":                     {"gl": "lv", "location": "Latvia"},
    "lebanon":                    {"gl": "lb", "location": "Lebanon"},
    "lesotho":                    {"gl": "ls", "location": "Lesotho"},
    "liberia":                    {"gl": "lr", "location": "Liberia"},
    "libya":                      {"gl": "ly", "location": "Libya"},
    "liechtenstein":              {"gl": "li", "location": "Liechtenstein"},
    "lithuania":                  {"gl": "lt", "location": "Lithuania"},
    "luxembourg":                 {"gl": "lu", "location": "Luxembourg"},
    "madagascar":                 {"gl": "mg", "location": "Madagascar"},
    "malawi":                     {"gl": "mw", "location": "Malawi"},
    "malaysia":                   {"gl": "my", "location": "Malaysia"},
    "maldives":                   {"gl": "mv", "location": "Maldives"},
    "mali":                       {"gl": "ml", "location": "Mali"},
    "malta":                      {"gl": "mt", "location": "Malta"},
    "marshall islands":           {"gl": "mh", "location": "Marshall Islands"},
    "mauritania":                 {"gl": "mr", "location": "Mauritania"},
    "mauritius":                  {"gl": "mu", "location": "Mauritius"},
    "mexico":                     {"gl": "mx", "location": "Mexico"},
    "micronesia":                 {"gl": "fm", "location": "Micronesia"},
    "moldova":                    {"gl": "md", "location": "Moldova"},
    "monaco":                     {"gl": "mc", "location": "Monaco"},
    "mongolia":                   {"gl": "mn", "location": "Mongolia"},
    "montenegro":                 {"gl": "me", "location": "Montenegro"},
    "morocco":                    {"gl": "ma", "location": "Morocco"},
    "mozambique":                 {"gl": "mz", "location": "Mozambique"},
    "myanmar":                    {"gl": "mm", "location": "Myanmar"},
    "namibia":                    {"gl": "na", "location": "Namibia"},
    "nauru":                      {"gl": "nr", "location": "Nauru"},
    "nepal":                      {"gl": "np", "location": "Nepal"},
    "netherlands":                {"gl": "nl", "location": "Netherlands"},
    "new zealand":                {"gl": "nz", "location": "New Zealand"},
    "nicaragua":                  {"gl": "ni", "location": "Nicaragua"},
    "niger":                      {"gl": "ne", "location": "Niger"},
    "nigeria":                    {"gl": "ng", "location": "Nigeria"},
    "north korea":                {"gl": "kp", "location": "North Korea"},
    "north macedonia":            {"gl": "mk", "location": "North Macedonia"},
    "norway":                     {"gl": "no", "location": "Norway"},
    "oman":                       {"gl": "om", "location": "Oman"},
    "pakistan":                   {"gl": "pk", "location": "Pakistan"},
    "palau":                      {"gl": "pw", "location": "Palau"},
    "panama":                     {"gl": "pa", "location": "Panama"},
    "papua new guinea":           {"gl": "pg", "location": "Papua New Guinea"},
    "paraguay":                   {"gl": "py", "location": "Paraguay"},
    "peru":                       {"gl": "pe", "location": "Peru"},
    "philippines":                {"gl": "ph", "location": "Philippines"},
    "poland":                     {"gl": "pl", "location": "Poland"},
    "portugal":                   {"gl": "pt", "location": "Portugal"},
    "qatar":                      {"gl": "qa", "location": "Qatar"},
    "romania":                    {"gl": "ro", "location": "Romania"},
    "russia":                     {"gl": "ru", "location": "Russia"},
    "rwanda":                     {"gl": "rw", "location": "Rwanda"},
    "saint kitts and nevis":      {"gl": "kn", "location": "Saint Kitts and Nevis"},
    "saint lucia":                {"gl": "lc", "location": "Saint Lucia"},
    "saint vincent and the grenadines": {"gl": "vc", "location": "Saint Vincent and the Grenadines"},
    "samoa":                      {"gl": "ws", "location": "Samoa"},
    "san marino":                 {"gl": "sm", "location": "San Marino"},
    "sao tome and principe":      {"gl": "st", "location": "Sao Tome and Principe"},
    "senegal":                    {"gl": "sn", "location": "Senegal"},
    "serbia":                     {"gl": "rs", "location": "Serbia"},
    "seychelles":                 {"gl": "sc", "location": "Seychelles"},
    "sierra leone":               {"gl": "sl", "location": "Sierra Leone"},
    "singapore":                  {"gl": "sg", "location": "Singapore"},
    "slovakia":                   {"gl": "sk", "location": "Slovakia"},
    "slovenia":                   {"gl": "si", "location": "Slovenia"},
    "solomon islands":            {"gl": "sb", "location": "Solomon Islands"},
    "somalia":                    {"gl": "so", "location": "Somalia"},
    "south africa":               {"gl": "za", "location": "South Africa"},
    "south korea":                {"gl": "kr", "location": "South Korea"},
    "south sudan":                {"gl": "ss", "location": "South Sudan"},
    "spain":                      {"gl": "es", "location": "Spain"},
    "sri lanka":                  {"gl": "lk", "location": "Sri Lanka"},
    "sudan":                      {"gl": "sd", "location": "Sudan"},
    "suriname":                   {"gl": "sr", "location": "Suriname"},
    "sweden":                     {"gl": "se", "location": "Sweden"},
    "switzerland":                {"gl": "ch", "location": "Switzerland"},
    "syria":                      {"gl": "sy", "location": "Syria"},
    "taiwan":                     {"gl": "tw", "location": "Taiwan"},
    "tajikistan":                 {"gl": "tj", "location": "Tajikistan"},
    "tanzania":                   {"gl": "tz", "location": "Tanzania"},
    "thailand":                   {"gl": "th", "location": "Thailand"},
    "timor-leste":                {"gl": "tl", "location": "Timor-Leste"},
    "togo":                       {"gl": "tg", "location": "Togo"},
    "tonga":                      {"gl": "to", "location": "Tonga"},
    "trinidad and tobago":        {"gl": "tt", "location": "Trinidad and Tobago"},
    "tunisia":                    {"gl": "tn", "location": "Tunisia"},
    "turkey":                     {"gl": "tr", "location": "Turkey"},
    "turkmenistan":               {"gl": "tm", "location": "Turkmenistan"},
    "tuvalu":                     {"gl": "tv", "location": "Tuvalu"},
    "uganda":                     {"gl": "ug", "location": "Uganda"},
    "ukraine":                    {"gl": "ua", "location": "Ukraine"},
    "uruguay":                    {"gl": "uy", "location": "Uruguay"},
    "uzbekistan":                 {"gl": "uz", "location": "Uzbekistan"},
    "vanuatu":                    {"gl": "vu", "location": "Vanuatu"},
    "vatican city":               {"gl": "va", "location": "Vatican City"},
    "venezuela":                  {"gl": "ve", "location": "Venezuela"},
    "vietnam":                    {"gl": "vn", "location": "Vietnam"},
    "yemen":                      {"gl": "ye", "location": "Yemen"},
    "zambia":                     {"gl": "zm", "location": "Zambia"},
    "zimbabwe":                   {"gl": "zw", "location": "Zimbabwe"},
}

_STRIP_WORDS = {"category", "brand", "product", "page", "search", "keyword", "query"}


def _clean_query(raw: str, country: str) -> str:
    tokens = raw.strip().split()
    country_key = country.strip().lower()
    country_info = COUNTRY_DATA.get(country_key, {})
    reject = set(_STRIP_WORDS)
    reject.add(country_key)
    if country_info:
        for word in country_info["location"].lower().split():
            reject.add(word)
    cleaned = [t for t in tokens if t.lower() not in reject]
    result = " ".join(cleaned).strip()
    return result if result else raw.strip()


class SerpScraper:
    def __init__(self):
        self.api_key = get_settings().SERP_API_KEY

    def _resolve_location(self, country: str) -> tuple[str, str]:
        key = country.strip().lower()
        info = COUNTRY_DATA.get(key)
        if not info:
            logger.warning(f"Country '{country}' not in COUNTRY_DATA — defaulting to United States.")
            info = {"gl": "us", "location": "United States"}
        return info["gl"], info["location"]

    # ── PAA: reads both people_also_ask AND related_questions ─────────────────
    def _extract_paa(self, data: dict) -> list[str]:
        """
        SerpAPI uses TWO key names for PAA depending on Google's layout:
          - people_also_ask    : standard accordion boxes
          - related_questions  : featured-snippet layout (what the JSON showed for
                                 'best moisturizer for dry skin')
        We check BOTH so PAA is never silently missed.
        """
        paa = []
        seen = set()

        def _add(q: str):
            q = q.strip()
            if q and q.lower() not in seen:
                seen.add(q.lower())
                paa.append(q)

        for item in data.get("people_also_ask", []):
            q = item.get("question", "") if isinstance(item, dict) else str(item)
            if q:
                _add(q)

        # KEY FIX: related_questions is the PAA key for featured-snippet SERPs
        for item in data.get("related_questions", []):
            q = item.get("question", "") if isinstance(item, dict) else str(item)
            if q:
                _add(q)

        if not paa:
            logger.debug(
                f"PAA=0 | keys={list(data.keys())} | "
                f"paa_present={'people_also_ask' in data} | "
                f"rq_present={'related_questions' in data}"
            )
        return paa

    # ── PAS ───────────────────────────────────────────────────────────────────
    def _extract_pas(self, data: dict) -> list[str]:
        pas = []
        seen = set()

        def _add(val):
            v = str(val).strip()
            if v and v.lower() not in seen:
                seen.add(v.lower())
                pas.append(v)

        for item in data.get("people_also_search_for", []):
            v = (item.get("query") or item.get("title") or item.get("name", "")) \
                if isinstance(item, dict) else item
            if v:
                _add(v)

        for organic in data.get("organic_results", []):
            for nested in organic.get("people_also_search", []):
                v = (nested.get("query") or nested.get("title") or nested.get("name", "")) \
                    if isinstance(nested, dict) else nested
                if v:
                    _add(v)

        for item in data.get("related_searches", []):
            if isinstance(item, dict):
                for nested in item.get("people_also_search", []):
                    v = (nested.get("query") or nested.get("title") or nested.get("name", "")) \
                        if isinstance(nested, dict) else nested
                    if v:
                        _add(v)
        return pas

    # ── Related searches + refine_this_search ────────────────────────────────
    def _extract_related(self, data: dict) -> list[str]:
        """
        Extract related_searches queries only.
        refine_this_search is NOT included here — it has its own method
        _extract_refine_searches() returning {query, link} pairs so it
        never pollutes the keyword list.
        """
        related = []
        seen = set()
        for item in data.get("related_searches", []):
            term = (item.get("query") if isinstance(item, dict) else str(item) or "").strip()
            if term and term.lower() not in seen:
                seen.add(term.lower())
                related.append(term)
        return related

    def _extract_refine_searches(self, data: dict) -> list[dict]:
        """
        Extract refine_this_search as {query, link} pairs.
        These are shopping filter chips (e.g. "For Men", "Ceramides", "Under $45").
        Stored separately so UI can show them as clickable interlinks,
        completely separate from SEO keywords.
        """
        results = []
        seen = set()
        for item in data.get("refine_this_search", []):
            if not isinstance(item, dict):
                continue
            query = item.get("query", "").strip()
            link  = item.get("link", "").strip()
            if query and query.lower() not in seen:
                seen.add(query.lower())
                results.append({"query": query, "link": link})
        return results
    def _extract_immersive_products(self, data: dict) -> list[dict]:
        """
        Extract product items from immersive_products OR shopping_results.

        NOTE: SerpAPI items inside 'immersive_products' do NOT have a 'category'
        field at the item level. The old filter 'if "popular" not in cat' was
        dropping every single item because category was always empty. Fixed to
        accept all items unconditionally.
        Falls back to shopping_results if immersive_products is absent.
        """
        products = []

        # Primary: immersive_products (Google's product carousel — brand/category searches)
        for item in data.get("immersive_products", []):
            if not isinstance(item, dict):
                continue
            # Accept all items — no category filter (items don't carry category field)
            products.append({
                "category":        item.get("category", "Popular products"),
                "thumbnail":       item.get("thumbnail", ""),
                "source":          item.get("source", ""),
                "title":           item.get("title", ""),
                "rating":          item.get("rating"),
                "reviews":         item.get("reviews"),
                "price":           item.get("price", ""),
                "extracted_price": item.get("extracted_price"),
                "link":            item.get("link", ""),
            })

        # Fallback: shopping_results (standard Google Shopping — product keyword searches)
        if not products:
            for item in data.get("shopping_results", []):
                if not isinstance(item, dict):
                    continue
                products.append({
                    "category":        "Shopping Results",
                    "thumbnail":       item.get("thumbnail", ""),
                    "source":          item.get("source", ""),
                    "title":           item.get("title", ""),
                    "rating":          item.get("rating"),
                    "reviews":         item.get("reviews"),
                    "price":           item.get("price", ""),
                    "extracted_price": item.get("extracted_price"),
                    "link":            item.get("link", ""),
                })

        src = "immersive" if data.get("immersive_products") else "shopping_results"
        logger.info(f"Immersive products extracted: {len(products)} (source: {src})")
        return products

    # ── NEW: More products (category == "More products") ─────────────────────
    def _extract_more_products(self, data: dict) -> list[dict]:
        """
        Extract 'More products' from immersive_products (separate from Popular).
        Shown only when user clicks 'Show More Products' button in the UI.
        """
        products = []
        for item in data.get("immersive_products", []):
            if not isinstance(item, dict):
                continue
            cat = item.get("category", "").lower()
            if "more" in cat and "popular" not in cat:
                products.append({
                    "category":        item.get("category", ""),
                    "thumbnail":       item.get("thumbnail", ""),
                    "source":          item.get("source", ""),
                    "title":           item.get("title", ""),
                    "rating":          item.get("rating"),
                    "reviews":         item.get("reviews"),
                    "price":           item.get("price", ""),
                    "extracted_price": item.get("extracted_price"),
                    "link":            item.get("link", ""),
                })
        return products

    # ── NEW: Inline videos ────────────────────────────────────────────────────
    def _extract_inline_videos(self, data: dict) -> list[dict]:
        """
        Extract inline_videos block from SERP response.
        Fields: position, title, link, thumbnail, channel, platform.
        """
        videos = []
        for item in data.get("inline_videos", []):
            if not isinstance(item, dict):
                continue
            videos.append({
                "position":  item.get("position", 0),
                "title":     item.get("title", ""),
                "link":      item.get("link", ""),
                "thumbnail": item.get("thumbnail", ""),
                "channel":   item.get("channel", ""),
                "platform":  item.get("platform", ""),
            })
        logger.info(f"Inline videos extracted: {len(videos)}")
        return videos

    # ── NEW: More videos (from perspectives + video_results) ─────────────────
    def _extract_more_videos(self, data: dict) -> list[dict]:
        """
        Extract additional video content beyond the 3 inline_videos.
        Sources checked:
          1. perspectives — items where source contains 'YouTube' or duration is present
          2. video_results — dedicated video results block (some SerpAPI responses)
        Shown only when user clicks 'Show More Videos' button in the UI.
        """
        videos = []
        seen_links = set()

        def _add_video(item: dict):
            link = item.get("link", "").strip()
            if not link or link in seen_links:
                return
            seen_links.add(link)
            thumbnails = item.get("thumbnails", [])
            thumb = thumbnails[0] if thumbnails else item.get("thumbnail", "")
            videos.append({
                "title":     item.get("title", ""),
                "link":      link,
                "thumbnail": thumb,
                "channel":   item.get("author", item.get("channel", "")),
                "platform":  item.get("source", item.get("platform", "YouTube")),
                "duration":  item.get("duration", ""),
                "date":      item.get("date", ""),
            })

        # Source 1: perspectives block — filter to video items
        for item in data.get("perspectives", []):
            if not isinstance(item, dict):
                continue
            source = item.get("source", "").lower()
            has_duration = bool(item.get("duration"))
            has_video = bool(item.get("video"))
            # Include if it looks like a video (has duration, is YouTube/Instagram/TikTok)
            if has_duration or has_video or any(
                s in source for s in ["youtube", "instagram", "tiktok", "facebook", "vimeo"]
            ):
                _add_video(item)

        # Source 2: video_results key (present in some SerpAPI responses)
        for item in data.get("video_results", []):
            if isinstance(item, dict):
                _add_video(item)

        logger.info(f"More videos extracted: {len(videos)}")
        return videos

    # ── NEW: AI Overview ──────────────────────────────────────────────────────
    def _extract_ai_overview(self, data: dict) -> tuple[list[str], list[dict]]:
        """
        Extract text blocks and references from the ai_overview section.
        Returns (text_blocks: list[str], references: list[dict]).
        """
        ai_data = data.get("ai_overview", {})
        if not ai_data:
            return [], []

        text_blocks = []
        for block in ai_data.get("text_blocks", []):
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "paragraph":
                snippet = block.get("snippet", "").strip()
                if snippet:
                    text_blocks.append(snippet)
            elif btype == "list":
                for li in block.get("list", []):
                    s = li.get("snippet", "").strip() if isinstance(li, dict) else str(li)
                    if s:
                        text_blocks.append(f"• {s}")

        references = []
        for ref in ai_data.get("references", []):
            if not isinstance(ref, dict):
                continue
            references.append({
                "title":   ref.get("title", ""),
                "link":    ref.get("link", ""),
                "snippet": ref.get("snippet", ""),
                "source":  ref.get("source", ""),
                "index":   ref.get("index", 0),
            })

        logger.info(f"AI Overview: {len(text_blocks)} text blocks, {len(references)} references")
        return text_blocks, references

    # ── Parse full response ───────────────────────────────────────────────────
    def _parse_response(self, data: dict) -> dict:
        results = []
        for item in data.get("organic_results", [])[:10]:
            results.append({
                "source":      "serp",
                "title":       item.get("title", ""),
                "description": item.get("snippet", ""),
                "url":         item.get("link", ""),
            })

        ai_text, ai_refs = self._extract_ai_overview(data)

        return {
            "results":               results,
            "related_searches":      self._extract_related(data),
            "people_also_ask":       self._extract_paa(data),
            "people_also_search_for": self._extract_pas(data),
            "immersive_products":    self._extract_immersive_products(data),
            "more_products":         self._extract_more_products(data),
            "inline_videos":         self._extract_inline_videos(data),
            "more_videos":           self._extract_more_videos(data),
            "refine_searches":       self._extract_refine_searches(data),
            "ai_overview_text":      ai_text,
            "ai_overview_references": ai_refs,
        }

    # ── Autocomplete ──────────────────────────────────────────────────────────
    def fetch_autocomplete(self, query: str, country: str) -> list[str]:
        if not self.api_key:
            return []

        gl, _ = self._resolve_location(country)
        suggestions = []
        seen = set()

        for letter in "abcdefghijklmnopqrstuvwxyz":
            try:
                params = {
                    "engine":  "google_autocomplete",
                    "q":       f"{query} {letter}",
                    "api_key": self.api_key,
                    "hl":      "en",
                    "gl":      gl,
                }
                with httpx.Client(timeout=8) as client:
                    resp = client.get(SERPAPI_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                for s in data.get("suggestions", []):
                    val = (s.get("value") or "").strip()
                    if val and val.lower() not in seen:
                        seen.add(val.lower())
                        suggestions.append(val)
                        if len(suggestions) >= 100:
                            return suggestions

            except Exception as e:
                logger.debug(f"Autocomplete letter='{letter}' failed: {e}")
                continue

        logger.info(f"Autocomplete: {len(suggestions)} suggestions for '{query}'")
        return suggestions

    # ── Main fetch: 3-tier fallback + PAA 2-stage fallback ───────────────────
    def fetch(self, query: str, country: str, num_results: int = 10) -> dict:
        """
        Fetch SERP data with 3-tier geo fallback and 2-stage PAA fallback.

        Tiers (stops at first tier returning organic results):
          1. gl + location  (targeted)
          2. gl only        (country code, broader)
          3. global         (last resort for micro-markets)

        PAA fallback: if paa=0 after organic results found, fires up to 2
        additional requests (gl-only then global) to fetch PAA/related_questions.
        """
        empty = {
            "results": [], "related_searches": [], "people_also_ask": [],
            "people_also_search_for": [], "autocomplete": [],
            "immersive_products": [], "more_products": [],
            "inline_videos": [], "more_videos": [],
            "refine_searches": [],
            "ai_overview_text": [], "ai_overview_references": [],
        }

        if not self.api_key:
            logger.warning("SerpAPI key not set. Skipping.")
            return empty

        clean_q = _clean_query(query, country)
        gl, location = self._resolve_location(country)

        # Query modification:
        # Keep single-word brand/category queries clean (>= 2 words = no append).
        # Appending 'products' to a 1-word brand name (e.g. 'nike products') changes
        # the SERP layout and SUPPRESSES the immersive_products carousel entirely.
        # Only bare 1-word queries get 'products' appended to trigger shopping results.
        serp_q = clean_q if len(clean_q.split()) >= 2 else f"{clean_q} products"

        tiers = [
            {"gl": gl, "location": location},
            {"gl": gl},
            {},
        ]

        base_params = {
            "engine":  "google",
            "q":       serp_q,
            "api_key": self.api_key,
            "num":     10,
            "start":   0,
            "hl":      "en",
        }

        last_parsed = {}
        for tier_num, overrides in enumerate(tiers, 1):
            try:
                params = {**base_params, **overrides}
                with httpx.Client(timeout=15) as client:
                    response = client.get(SERPAPI_URL, params=params)
                    response.raise_for_status()
                    data = response.json()

                parsed = self._parse_response(data)
                last_parsed = parsed

                logger.info(
                    f"SERP tier={tier_num} | raw='{query}' clean='{clean_q}' serp='{serp_q}' "
                    f"gl={overrides.get('gl','-')} loc='{overrides.get('location','-')}' | "
                    f"organic={len(parsed['results'])} related={len(parsed['related_searches'])} "
                    f"paa={len(parsed['people_also_ask'])} pas={len(parsed['people_also_search_for'])} "
                    f"popular={len(parsed['immersive_products'])} more_prod={len(parsed['more_products'])} "
                    f"videos={len(parsed['inline_videos'])} more_vid={len(parsed['more_videos'])} "
                    f"refine={len(parsed['refine_searches'])} "
                    f"ai_refs={len(parsed['ai_overview_references'])}"
                )

                if parsed["results"]:
                    # PAA 2-stage fallback for small markets
                    if not parsed["people_also_ask"]:
                        for paa_attempt, paa_ov in enumerate([
                            {"gl": gl, "num": 10, "device": "desktop"},
                            {"num": 10, "device": "desktop"},
                        ], 1):
                            try:
                                paa_params = {**base_params, "q": serp_q, **paa_ov}
                                with httpx.Client(timeout=10) as pc:
                                    pr = pc.get(SERPAPI_URL, params=paa_params)
                                    pr.raise_for_status()
                                    pd2 = pr.json()
                                extra_paa = self._extract_paa(pd2)
                                extra_pas = self._extract_pas(pd2)
                                if extra_paa:
                                    parsed["people_also_ask"] = extra_paa
                                if extra_pas:
                                    parsed["people_also_search_for"] = extra_pas
                                logger.info(
                                    f"SERP PAA stage={paa_attempt} | paa={len(extra_paa)} pas={len(extra_pas)}"
                                )
                                if extra_paa:
                                    break
                            except Exception as e:
                                logger.warning(f"PAA stage={paa_attempt} failed: {e}")

                    # Autocomplete with query-word relevance filter
                    autocomplete = self.fetch_autocomplete(clean_q, country)
                    query_words = set(clean_q.lower().split())
                    autocomplete = [s for s in autocomplete if any(w in s.lower() for w in query_words)]
                    parsed["autocomplete"] = autocomplete
                    return parsed

                if tier_num < len(tiers):
                    logger.warning(f"SERP tier={tier_num} → 0 organic. Trying tier {tier_num+1}...")

            except Exception as e:
                logger.error(f"SERP tier={tier_num} failed: {e}")
                continue

        logger.error(f"SERP: all tiers returned 0 results for '{clean_q}'.")
        last_parsed["autocomplete"] = []
        return last_parsed if last_parsed else empty