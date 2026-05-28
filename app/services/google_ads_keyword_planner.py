"""
Optional Google Ads Keyword Planner integration via KeywordPlanIdeaService.GenerateKeywordIdeas.

Requires package: google-ads
Environment (typical):
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CLIENT_ID
  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN
  GOOGLE_ADS_CUSTOMER_ID          # Ads account customer id (digits, dashes optional)
  GOOGLE_ADS_LOGIN_CUSTOMER_ID    # Optional MCC / manager id when using manager access
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.services.country_registry import COUNTRY_CODES, language_for_country

logger = logging.getLogger(__name__)

# Fast-path cache for common countries (avoids an extra API round-trip).
_PLANNER_GEO_FAST_PATH: Dict[str, str] = {
    "United States": "geoTargetConstants/2840",
    "United Kingdom": "geoTargetConstants/2826",
    "Canada": "geoTargetConstants/2124",
    "Australia": "geoTargetConstants/2036",
    "India": "geoTargetConstants/2356",
    "Germany": "geoTargetConstants/2276",
    "France": "geoTargetConstants/2250",
    "Spain": "geoTargetConstants/2724",
    "Italy": "geoTargetConstants/2380",
    "Brazil": "geoTargetConstants/2076",
    "Mexico": "geoTargetConstants/2484",
    "Saudi Arabia": "geoTargetConstants/2682",
    "United Arab Emirates": "geoTargetConstants/2784",
    "Qatar": "geoTargetConstants/2760",
    "Singapore": "geoTargetConstants/2702",
    "Japan": "geoTargetConstants/2392",
    "South Korea": "geoTargetConstants/2410",
    "Netherlands": "geoTargetConstants/2528",
    "Poland": "geoTargetConstants/2616",
    "Turkey": "geoTargetConstants/2792",
    "South Africa": "geoTargetConstants/2710",
    "Pakistan": "geoTargetConstants/2586",
    "Philippines": "geoTargetConstants/2608",
    "Indonesia": "geoTargetConstants/2360",
    "Thailand": "geoTargetConstants/2764",
    "Vietnam": "geoTargetConstants/2824",
    "Malaysia": "geoTargetConstants/2458",
    "New Zealand": "geoTargetConstants/2554",
    "Ireland": "geoTargetConstants/2372",
    "Switzerland": "geoTargetConstants/2756",
    "Sweden": "geoTargetConstants/2750",
    "Norway": "geoTargetConstants/2578",
    "Denmark": "geoTargetConstants/2208",
    "Finland": "geoTargetConstants/2246",
    "Belgium": "geoTargetConstants/2056",
    "Austria": "geoTargetConstants/2040",
    "Portugal": "geoTargetConstants/2620",
    "Greece": "geoTargetConstants/2300",
    "Israel": "geoTargetConstants/2376",
    "Egypt": "geoTargetConstants/2818",
    "Nigeria": "geoTargetConstants/2566",
    "Kenya": "geoTargetConstants/2404",
    "Argentina": "geoTargetConstants/2032",
    "Colombia": "geoTargetConstants/2170",
    "Chile": "geoTargetConstants/2152",
    "China": "geoTargetConstants/2156",
    "Taiwan": "geoTargetConstants/2158",
    "Hong Kong": "geoTargetConstants/2344",
    "Russia": "geoTargetConstants/2643",
    "Ukraine": "geoTargetConstants/2804",
}

_GEO_TARGET_CACHE: Dict[str, str] = dict(_PLANNER_GEO_FAST_PATH)

LANGUAGE_CONSTANTS: Dict[str, str] = {
    "English": "languageConstants/1000",
    "German": "languageConstants/1001",
    "French": "languageConstants/1002",
    "Spanish": "languageConstants/1003",
    "Italian": "languageConstants/1004",
    "Japanese": "languageConstants/1005",
    "Danish": "languageConstants/1006",
    "Dutch": "languageConstants/1007",
    "Finnish": "languageConstants/1008",
    "Korean": "languageConstants/1009",
    "Portuguese": "languageConstants/1010",
    "Norwegian": "languageConstants/1011",
    "Swedish": "languageConstants/1012",
    "Chinese": "languageConstants/1017",
    "Indonesian": "languageConstants/1025",
    "Turkish": "languageConstants/1037",
    "Arabic": "languageConstants/1019",
    "Hindi": "languageConstants/1022",
    "Polish": "languageConstants/1030",
    "Russian": "languageConstants/1031",
    "Thai": "languageConstants/1044",
    "Vietnamese": "languageConstants/1045",
    "Greek": "languageConstants/1023",
    "Czech": "languageConstants/1021",
    "Romanian": "languageConstants/1032",
    "Hungarian": "languageConstants/1024",
    "Hebrew": "languageConstants/1027",
    "Persian": "languageConstants/1064",
    "Bengali": "languageConstants/1056",
    "Malay": "languageConstants/1102",
    "Ukrainian": "languageConstants/1036",
    "Croatian": "languageConstants/1039",
    "Slovak": "languageConstants/1033",
    "Bulgarian": "languageConstants/1020",
    "Serbian": "languageConstants/1035",
    "Slovenian": "languageConstants/1034",
    "Icelandic": "languageConstants/1026",
    "Georgian": "languageConstants/1087",
    "Armenian": "languageConstants/1095",
    "Azerbaijani": "languageConstants/1096",
    "Uzbek": "languageConstants/1093",
    "Swahili": "languageConstants/1089",
    "Amharic": "languageConstants/1090",
    "Sinhala": "languageConstants/1086",
    "Nepali": "languageConstants/1091",
    "Khmer": "languageConstants/1103",
    "Lao": "languageConstants/1104",
    "Burmese": "languageConstants/1105",
    "Kinyarwanda": "languageConstants/1000",
}


def _language_for_country(country: str) -> str:
    lang_name = language_for_country(country)
    return LANGUAGE_CONSTANTS.get(lang_name, "languageConstants/1000")


def _resolve_geo_target(client, country: str) -> str:
    """Resolve Google Ads geoTargetConstants for any country in country_registry."""
    country = (country or "").strip()
    if not country:
        return "geoTargetConstants/2840"
    if country in _GEO_TARGET_CACHE:
        return _GEO_TARGET_CACHE[country]

    try:
        gtc_service = client.get_service("GeoTargetConstantService")
        request = client.get_type("SuggestGeoTargetConstantsRequest")
        request.locale = "en"
        iso = COUNTRY_CODES.get(country)
        if iso:
            request.country_code = iso
        request.location_names.append(country)

        response = gtc_service.suggest_geo_target_constants(request=request)
        best_country = None
        best_any = None
        for suggestion in response.geo_target_constant_suggestions:
            gtc = suggestion.geo_target_constant
            resource = gtc.resource_name
            target_type = str(getattr(gtc, "target_type", "") or "")
            if not best_any:
                best_any = resource
            if target_type == "Country" or "COUNTRY" in target_type.upper():
                if gtc.country_code == iso or not iso:
                    best_country = resource
                    break
                if not best_country:
                    best_country = resource

        resolved = best_country or best_any
        if resolved:
            _GEO_TARGET_CACHE[country] = resolved
            logger.info("Resolved geo target for %s -> %s", country, resolved)
            return resolved
    except Exception as e:
        logger.warning("GeoTargetConstant suggest failed for %r: %s", country, e)

    fallback = "geoTargetConstants/2840"
    _GEO_TARGET_CACHE[country] = fallback
    return fallback


def is_google_ads_planner_configured() -> bool:
    required = (
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
    )
    return all(os.getenv(k, "").strip() for k in required)


def _normalize_customer_id(cid: str) -> str:
    return "".join(ch for ch in cid if ch.isdigit())


def _normalize_seed_url(url: str) -> Optional[str]:
    u = (url or "").strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        p = urlparse(u)
        if p.scheme and p.netloc:
            return u
    except Exception:
        pass
    return None


def _build_client():
    from google.ads.googleads.client import GoogleAdsClient

    cfg: Dict[str, Any] = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip(),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip(),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "").strip(),
        "use_proto_plus": True,
    }
    login = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()
    if login:
        cfg["login_customer_id"] = _normalize_customer_id(login)
    return GoogleAdsClient.load_from_dict(cfg)


def _micros_to_currency(m_low: Optional[int], m_high: Optional[int]) -> Optional[float]:
    if m_low is None and m_high is None:
        return None
    vals = []
    for m in (m_low, m_high):
        if m is not None and m > 0:
            vals.append(m / 1_000_000.0)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def _idea_row(text: str, metrics) -> Dict[str, Any]:
    vol = getattr(metrics, "avg_monthly_searches", None) or 0
    comp = getattr(metrics, "competition", None)
    comp_name = ""
    if comp is not None:
        comp_name = getattr(comp, "name", str(comp)) or ""
    idx = getattr(metrics, "competition_index", None)
    kd_display = idx if idx is not None else (comp_name or "—")

    low_bid = getattr(metrics, "low_top_of_page_bid_micros", None)
    high_bid = getattr(metrics, "high_top_of_page_bid_micros", None)
    cpc = _micros_to_currency(low_bid, high_bid)

    return {
        "keyword": text,
        "volume": int(vol) if vol else 0,
        "difficulty": kd_display,
        "cpc": cpc,
        "competition_label": comp_name,
    }


def _collect_ideas(client, request) -> List[Dict[str, Any]]:
    svc = client.get_service("KeywordPlanIdeaService")
    out: List[Dict[str, Any]] = []
    seen: set = set()
    stream = svc.generate_keyword_ideas(request=request)
    for idea in stream.results:
        text = getattr(idea, "text", None) or ""
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        m = getattr(idea, "keyword_idea_metrics", None)
        if m is None:
            continue
        out.append(_idea_row(text, m))
    return out


def _single_request(client, customer_id: str, geo: str, lang: str, **seed_kwargs) -> Any:
    req = client.get_type("GenerateKeywordIdeasRequest")
    req.customer_id = customer_id
    req.language = lang
    req.geo_target_constants.append(geo)
    req.include_adult_keywords = False
    if "keyword_seed_keywords" in seed_kwargs:
        ks = client.get_type("KeywordSeed")
        for kw in seed_kwargs["keyword_seed_keywords"]:
            if kw:
                ks.keywords.append(kw)
        req.keyword_seed = ks
    if "url_seed_urls" in seed_kwargs:
        us = client.get_type("UrlSeed")
        for u in seed_kwargs["url_seed_urls"]:
            if u:
                us.url = u
        req.url_seed = us
    return req


def fetch_keyword_planner_ideas(
    keyword: str,
    country: str,
    seed_url: Optional[str] = None,
    limit: int = 100,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Returns (rows, error_message). Each row: keyword, volume, difficulty, cpc (float or None).
    Supports every country in app.services.country_registry (same list as Studio Pipeline SERP).
    """
    if not is_google_ads_planner_configured():
        return [], None

    try:
        from google.ads.googleads.errors import GoogleAdsException
    except ImportError:
        return [], "Install the `google-ads` package to use Keyword Planner (pip install google-ads)."

    cust_raw = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").strip()
    customer_id = _normalize_customer_id(cust_raw)
    if not customer_id:
        return [], "GOOGLE_ADS_CUSTOMER_ID is invalid."

    if country and country not in COUNTRY_CODES:
        logger.warning(
            "Country %r not in registry — using United States geo fallback. "
            "Use a name from the Country dropdown (e.g. 'Saudi Arabia').",
            country,
        )

    rows: List[Dict[str, Any]] = []
    try:
        client = _build_client()
        geo = _resolve_geo_target(client, country)
        lang = _language_for_country(country)

        if (keyword or "").strip():
            req_kw = _single_request(
                client,
                customer_id,
                geo,
                lang,
                keyword_seed_keywords=[keyword.strip()],
            )
            rows.extend(_collect_ideas(client, req_kw))

        norm_url = _normalize_seed_url(seed_url or "")
        if norm_url:
            req_url = _single_request(
                client,
                customer_id,
                geo,
                lang,
                url_seed_urls=[norm_url],
            )
            rows.extend(_collect_ideas(client, req_url))

        by_lower: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            k = (r.get("keyword") or "").strip().lower()
            if not k:
                continue
            if k not in by_lower:
                by_lower[k] = r
            elif (r.get("volume") or 0) > (by_lower[k].get("volume") or 0):
                by_lower[k] = r
        merged = list(by_lower.values())[: max(1, limit)]
        return merged, None
    except GoogleAdsException as ex:
        msg = ex.failure.errors[0].message if ex.failure.errors else str(ex)
        logger.warning("GoogleAdsException: %s", msg)
        return [], msg
    except Exception as e:
        logger.exception("Keyword Planner error: %s", e)
        return [], str(e)
