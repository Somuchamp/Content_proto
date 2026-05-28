from openai import OpenAI
import json
import logging
import re
from collections import Counter, defaultdict

from app.config import get_settings
from app.models.schemas import ProcessedInsights

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data analyst specializing in e-commerce SEO and market research.
Analyze the provided raw scraped data and extract structured insights based on current market trends.
Respond ONLY with valid JSON. No markdown, no preamble."""

USER_PROMPT = """
Analyze this raw scraped data for the e-commerce {content_type} "{name}" in {country}.
Focus on trends and signals from the past 1 year only.

Raw data:
---
{context}
---

Return ONLY this JSON (no markdown, no extra keys):
{{
  "keywords": ["10-15 high-value SEO keywords relevant to {name} in {country}"],
  "trending_topics": ["5-8 currently trending product topics or features"],
  "faqs": ["5-8 common buyer questions about {name}"],
  "market_trends": ["4-6 market and consumer behavior trends from last 1 year"]
}}
"""

# High-value commercial intent words that increase real-world keyword difficulty
_HARD_WORDS = {"best", "top", "review", "vs", "compare", "alternative", "buy"}
_MEDIUM_WORDS = {"cheap", "price", "cost", "deal", "discount", "affordable", "sale"}
_EASY_WORDS = {"what", "how", "why", "when", "where", "is", "are", "can"}

# Stopwords to exclude from trend extraction
_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "your",
    "are", "was", "were", "has", "had", "its", "not", "but", "they",
    "their", "been", "more", "very", "just", "also", "like", "will",
    "when", "than", "into", "about", "some", "each", "which", "there",
    "can", "use", "used", "using", "get", "got", "our", "you",
}


class DataProcessor:
    """
    Step 3 — Data Processing:
    Extracts keywords, FAQs, trending topics, market trends, keyword clusters,
    keyword difficulty, and source-specific trends (Reddit/YouTube).
    """

    def __init__(self):
        settings = get_settings()
        kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_API_BASE:
            kwargs["base_url"] = settings.OPENAI_API_BASE
        self.client = OpenAI(**kwargs)

    # ──────────────────────────────────────────────────────────────────────
    # REDDIT TREND MINING
    # FIX: now filters to reddit-only items and requires relevance to query.
    # ──────────────────────────────────────────────────────────────────────
    def extract_reddit_trends(self, items: list[dict], query: str) -> list[str]:
        """
        Extract trending phrases from Reddit items only, relevant to the query.

        FIXES vs old version:
          1. query_words now includes merged variants: "skin care" -> also adds "skincare"
             so posts using the one-word form are not missed.
          2. Relevance check is now applied to the FULL title string first (fast path),
             not just extracted multi-word phrases. If ANY query word appears anywhere
             in the title, the item is included. This catches "Best moisturizer for dry
             skin" which contains "skin" even though "skin care" as a phrase is absent.
          3. Phrases are extracted from relevant items only (not all reddit text mixed),
             so frequency counts reflect actual discussion topics, not noise.
          4. Single-word trending terms are also captured (min 4 chars, not stopword)
             when phrase extraction yields too few results.
        """
        # Build query word set including concatenated variant
        raw_words = re.findall(r"[a-z]{3,}", query.lower())
        query_words = set(raw_words)
        # Add merged form: "skin care" -> also match "skincare"
        if len(raw_words) >= 2:
            query_words.add("".join(raw_words))   # skincare, haircare, etc.

        relevant_texts = []
        for item in items:
            if item.get("source", "").lower() != "reddit":
                continue
            title = item.get("title", "").lower()
            desc  = item.get("description", "").lower()
            combined_item = f"{title} {desc}"
            # RELEVANCE: ANY query word (or merged form) must appear somewhere
            # in the title or description — not just in extracted phrases.
            if any(w in combined_item for w in query_words):
                relevant_texts.append(combined_item)

        if not relevant_texts:
            return []

        all_text = " ".join(relevant_texts)

        # Extract 2-4 word phrases from relevant items only
        phrases = re.findall(r"\b[a-z]{3,}(?:\s[a-z]{3,}){1,3}\b", all_text)
        relevant_phrases = [
            p for p in phrases
            if not all(w in _STOPWORDS for w in p.split())
            and any(w in query_words for w in p.split())
        ]
        counts = Counter(relevant_phrases)
        results = [p for p, _ in counts.most_common(10)]

        # Fallback: if fewer than 3 phrases found, supplement with single keywords
        if len(results) < 3:
            words = re.findall(r"\b[a-z]{4,}\b", all_text)
            word_counts = Counter(
                w for w in words
                if w not in _STOPWORDS and w in query_words or
                any(q in w or w in q for q in query_words if len(q) >= 4)
            )
            for w, _ in word_counts.most_common(5):
                if w not in results:
                    results.append(w)

        return results[:10]

    # ──────────────────────────────────────────────────────────────────────
    # YOUTUBE TREND SIGNALS
    # FIX: now returns {title, url} dicts filtered to query-relevant items.
    # ──────────────────────────────────────────────────────────────────────
    def extract_youtube_trends(self, items: list[dict], query: str) -> list[dict]:
        """
        Return YouTube items (title + url) that are relevant to the query.
        Relevance = at least 2 query keywords appear in the title.
        Capped at 10 results.
        """
        query_words = set(re.findall(r"[a-z]{3,}", query.lower()))
        results = []

        for item in items:
            if item.get("source", "").lower() != "youtube":
                continue
            title = item.get("title", "").strip()
            url   = item.get("url", "").strip()
            if not title:
                continue
            title_words = set(re.findall(r"[a-z]{3,}", title.lower()))
            overlap = len(title_words & query_words)
            if overlap >= 2:
                results.append({"title": title, "url": url})

        return results[:10]

    # ──────────────────────────────────────────────────────────────────────
    # KEYWORD CLUSTERING
    # FIX: groups by shared meaningful stem (first non-stopword), not just
    # the first token (which was often a stopword or article).
    # ──────────────────────────────────────────────────────────────────────
    def cluster_keywords(self, keywords: list[str]) -> list[list[str]]:
        """
        Group keywords by their first meaningful word (non-stopword, 4+ chars).
        Ungroupable keywords go into an 'other' bucket.
        Returns clusters with 2+ members first, then singles.
        """
        clusters: dict[str, list[str]] = defaultdict(list)

        for kw in keywords:
            words = [w for w in kw.lower().split()
                     if w not in _STOPWORDS and len(w) >= 4]
            root = words[0] if words else kw.split()[0]
            clusters[root].append(kw)

        # Sort: larger clusters first
        sorted_clusters = sorted(clusters.values(), key=lambda c: -len(c))
        return sorted_clusters

    # ──────────────────────────────────────────────────────────────────────
    # KEYWORD DIFFICULTY ESTIMATION
    # FIX: uses intent signals + word count + source frequency weighting.
    # Scale: 0-100 (higher = harder to rank for).
    # ──────────────────────────────────────────────────────────────────────
    def keyword_difficulty(self, keywords: list[str]) -> dict[str, int]:
        """
        Heuristic keyword difficulty score (0–100).

        Scoring logic:
          Base: 30 (all keywords start at moderate difficulty)
          +20  : contains a high-competition intent word (best, review, vs)
          +15  : contains a commercial intent word (buy, price, cheap)
          -10  : contains an informational word (how, what, why) — easier
          +5   : each additional word beyond 2 (shorter = harder)
          -5   : each word beyond 4 (very long-tail = easier)
          Clamped to [5, 95]
        """
        difficulty = {}
        for kw in keywords:
            words = kw.lower().split()
            score = 30

            if any(w in _HARD_WORDS for w in words):
                score += 20
            if any(w in _MEDIUM_WORDS for w in words):
                score += 15
            if any(w in _EASY_WORDS for w in words):
                score -= 10

            word_count = len(words)
            if word_count <= 2:
                score += 5
            elif word_count >= 5:
                score -= (word_count - 4) * 5

            difficulty[kw] = max(5, min(95, score))

        return difficulty

    # ──────────────────────────────────────────────────────────────────────
    # MAIN PROCESS
    # ──────────────────────────────────────────────────────────────────────
    def process(
        self,
        name: str,
        content_type: str,
        country: str,
        context: str,
        all_items: list[dict] | None = None,   # FIX: raw items for source-specific extraction
        serp_related: list[str] | None = None,
        serp_paa: list[str] | None = None,
        serp_pas: list[str] | None = None,     # FIX: people_also_search_for
        autocomplete: list[str] | None = None,
    ) -> ProcessedInsights:

        prompt = USER_PROMPT.format(
            name=name,
            content_type=content_type,
            country=country,
            context=context or "No external data available.",
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1200,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            parsed = {"keywords": [], "trending_topics": [], "faqs": [], "market_trends": []}

        ai_keywords = parsed.get("keywords", [])

        # ── Keyword pipeline ─────────────────────────────────────────────
        # Priority: SERP related (most trusted) > AI keywords > autocomplete
        # autocomplete is stored separately for the UI tab but only top-15
        # are merged into the main keyword list sent to content_generator.
        # This prevents autocomplete noise (e.g. "skin care bd") from filling
        # up the prompt and causing 36 keywords-not-found warnings.
        clean_autocomplete = (autocomplete or [])[:15]   # top-15 autocomplete only
        raw_keywords = list(dict.fromkeys(
            (serp_related or [])          # SERP related: best signal, use all
            + ai_keywords                 # AI-extracted: topic-relevant
            + clean_autocomplete          # Autocomplete: supplementary
        ))[:25]                           # hard cap at 25 — LLM can embed these

        # ── FAQs: PAA questions first, then AI-generated ─────────────────
        faqs = list(dict.fromkeys(
            (serp_paa or []) + parsed.get("faqs", [])
        ))[:12]

        # ── Source-specific trends ────────────────────────────────────────
        items = all_items or []
        query_str = f"{name} {content_type}"
        reddit_trends  = self.extract_reddit_trends(items, query_str)
        youtube_trends = self.extract_youtube_trends(items, query_str)

        # YouTube trends for trending_topics: extract titles as strings
        yt_titles = [t["title"] for t in youtube_trends]

        # ── Trending topics: reddit + youtube + AI, deduplicated ──────────
        trending_topics = list(dict.fromkeys(
            reddit_trends + yt_titles + parsed.get("trending_topics", [])
        ))[:12]

        # ── Clusters & difficulty ─────────────────────────────────────────
        clusters   = self.cluster_keywords(raw_keywords)
        difficulty = self.keyword_difficulty(raw_keywords)

        logger.info(
            f"DataProcessor | keywords={len(raw_keywords)} clusters={len(clusters)} "
            f"faqs={len(faqs)} reddit_trends={len(reddit_trends)} "
            f"yt_trends={len(youtube_trends)} pas={len(serp_pas or [])}"
        )

        return ProcessedInsights(
            keywords               = raw_keywords,
            autocomplete_keywords  = autocomplete or [],
            keyword_clusters       = clusters,
            keyword_difficulty     = difficulty,
            reddit_trends          = reddit_trends,
            youtube_trends         = youtube_trends,   # list of {title, url} dicts
            people_also_ask        = serp_paa or [],
            people_also_search_for = serp_pas or [],   # FIX: was missing entirely
            trending_topics        = trending_topics,
            faqs                   = faqs,
            market_trends          = parsed.get("market_trends", []),
        )