"""
Shared country list aligned with app/scrapers/serp_scraper.COUNTRY_DATA.
Used by DataForSEO services, Deep Research / Competitor Analysis dropdowns, and Google Ads Keyword Planner.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

_REGISTRY_PATH = Path(__file__).resolve().parent / "country_codes.json"

# Primary language for Keyword Planner / DataForSEO (ISO 3166-1 alpha-2 -> language name)
_ISO_PRIMARY_LANGUAGE: Dict[str, str] = {
    "US": "English", "GB": "English", "CA": "English", "AU": "English", "NZ": "English",
    "IE": "English", "IN": "English", "SG": "English", "PH": "English", "PK": "English",
    "NG": "English", "KE": "English", "ZA": "English", "GH": "English", "JM": "English",
    "TT": "English", "BS": "English", "BB": "English", "BZ": "English", "MT": "English",
    "CY": "English", "UG": "English",
    "DE": "German", "AT": "German", "CH": "German", "LI": "German",
    "FR": "French", "BE": "French", "LU": "French", "MC": "French", "SN": "French",
    "MA": "Arabic", "TN": "Arabic", "DZ": "Arabic",
    "ES": "Spanish", "MX": "Spanish", "AR": "Spanish", "CO": "Spanish", "CL": "Spanish",
    "PE": "Spanish", "VE": "Spanish", "EC": "Spanish", "GT": "Spanish", "CU": "Spanish",
    "BO": "Spanish", "PY": "Spanish", "UY": "Spanish", "CR": "Spanish", "PA": "Spanish",
    "DO": "Spanish", "HN": "Spanish", "NI": "Spanish", "SV": "Spanish",
    "IT": "Italian", "SM": "Italian", "VA": "Italian",
    "PT": "Portuguese", "BR": "Portuguese", "AO": "Portuguese", "MZ": "Portuguese",
    "NL": "Dutch",
    "PL": "Polish", "RU": "Russian", "UA": "Ukrainian", "BY": "Russian",
    "JP": "Japanese", "KR": "Korean", "CN": "Chinese", "TW": "Chinese", "HK": "Chinese",
    "TH": "Thai", "VN": "Vietnamese", "ID": "Indonesian", "MY": "Malay",
    "SA": "Arabic", "AE": "Arabic", "EG": "Arabic", "IQ": "Arabic", "JO": "Arabic",
    "KW": "Arabic", "LB": "Arabic", "LY": "Arabic", "OM": "Arabic", "QA": "Arabic",
    "SY": "Arabic", "YE": "Arabic", "BH": "Arabic",
    "TR": "Turkish", "GR": "Greek", "RO": "Romanian", "HU": "Hungarian", "CZ": "Czech",
    "SK": "Slovak", "BG": "Bulgarian", "HR": "Croatian", "RS": "Serbian", "SI": "Slovenian",
    "SE": "Swedish", "NO": "Norwegian", "DK": "Danish", "FI": "Finnish", "IS": "Icelandic",
    "IL": "Hebrew", "IR": "Persian", "AF": "Persian", "BD": "Bengali", "LK": "Sinhala",
    "NP": "Nepali", "KH": "Khmer", "LA": "Lao", "MM": "Burmese", "KZ": "Russian",
    "UZ": "Uzbek", "GE": "Georgian", "AM": "Armenian", "AZ": "Azerbaijani",
    "ET": "Amharic", "TZ": "Swahili", "RW": "Kinyarwanda",
}


def _load_country_codes() -> Dict[str, str]:
    if _REGISTRY_PATH.is_file():
        try:
            data = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                return {str(k): str(v).upper() for k, v in data.items()}
        except Exception:
            pass
    try:
        from app.scrapers.serp_scraper import COUNTRY_DATA
        codes: Dict[str, str] = {}
        for info in COUNTRY_DATA.values():
            loc = info.get("location", "").strip()
            gl = (info.get("gl") or "").strip().upper()
            if loc and gl and len(gl) == 2 and loc not in codes:
                codes[loc] = gl
        return codes
    except Exception:
        return dict(_FALLBACK_COUNTRY_CODES)


_FALLBACK_COUNTRY_CODES: Dict[str, str] = {
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "India": "IN",
    "Germany": "DE",
    "France": "FR",
    "Spain": "ES",
    "Italy": "IT",
    "Brazil": "BR",
    "Mexico": "MX",
}

COUNTRY_CODES: Dict[str, str] = _load_country_codes()
SUPPORTED_COUNTRIES: List[str] = sorted(COUNTRY_CODES.keys())


def language_for_country(country: str) -> str:
    iso = COUNTRY_CODES.get(country, "US")
    return _ISO_PRIMARY_LANGUAGE.get(iso, "English")


COUNTRY_LANGUAGES: Dict[str, str] = {name: language_for_country(name) for name in COUNTRY_CODES}
