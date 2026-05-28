from openai import OpenAI
import json
import logging
from app.config import get_settings
from app.models.schemas import HeadingSection, ProcessedInsights

logger = logging.getLogger(__name__)


def _sanitize_json_string(raw: str) -> str:
    """
    Fix literal (unescaped) control characters inside JSON string values.

    When the H2/H3 bullet prompt generates multi-line body text, OpenAI
    sometimes returns the JSON with literal newline / tab / carriage-return
    characters inside the string values instead of the escaped forms
    (\\n, \\t, \\r).  json.loads() treats these as 'Invalid control character'
    and raises JSONDecodeError.

    This function walks the string character-by-character and escapes
    control characters ONLY when they appear inside a JSON string value
    (i.e. between un-escaped double-quotes), leaving all structural
    JSON tokens (braces, brackets, colons, commas) untouched.
    """
    result = []
    in_string = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if in_string:
            if ch == '\\' and i + 1 < len(raw):
                # Already-escaped sequence — keep both chars as-is
                result.append(ch)
                result.append(raw[i + 1])
                i += 2
                continue
            elif ch == '"':
                in_string = False
                result.append(ch)
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ord(ch) < 0x20:
                # Other control chars — drop them
                pass
            else:
                result.append(ch)
        else:
            if ch == '"':
                in_string = True
            result.append(ch)
        i += 1
    return ''.join(result)

# ── Shared system prompt ───────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert e-commerce SEO content writer specializing in category,
brand, and blog content. Your writing is informative, engaging, and keyword-rich.

IMPORTANT CONTEXT FOR WRITING:
- All content should internally consider the current market period (2026) for relevance.
- DO NOT mention any dates, months, or years explicitly in the generated content.
- Content must follow Google's EEAT guidelines.
- Content must reference Ubuy as a global cross-border e-commerce marketplace where relevant.
- Content must remain strictly Ubuy-specific and MUST NOT mention or compare any other marketplace.

Respond ONLY with valid JSON. No markdown, no preamble."""

# -------03-04-26------
# ── Category / Brand prompt ────────────────────────────────────────────────────
# ECOMMERCE_PROMPT = """
# Write SEO-optimized content for an e-commerce {content_type} page for: "{name}"
# Target country: {country}

# WRITING REQUIREMENTS:
# - DO NOT mention dates, months, or years anywhere.
# - Strong EEAT signals throughout.
# - Mention Ubuy naturally as a global marketplace delivering to {country}.
# - Ubuy + {country} contextual relevance: international availability, cross-border shopping.
# - Ubuy-focused ONLY — no other marketplace mentioned.
# - Headings and body must be highly keyword-rich and SEO optimized.
# - Each body section: 4-6 sentences of detailed, EEAT-compliant text.

# Market research insights:
# - Keywords: {keywords}
# - Trending topics: {trending_topics}
# - Common FAQs: {faqs}
# - Market trends: {market_trends}

# Additional context:
# ---
# {context}
# ---

# Generate exactly {max_headings} heading sections using these types as guide:
# - Introduction to the {content_type}
# - Key features and benefits
# - Popular products in this {content_type}
# - Why customers prefer this {content_type}
# - Buying considerations
# - Latest trends
# - Frequently asked questions

# KEYWORD RULES:
# 1. Every section MUST contain 2-3 keywords from the list, used naturally.
# 2. Distribute keywords across ALL sections — never cluster in one section.
# 3. High-ranking keywords (listed first) appear more frequently.
# 4. Each heading should contain a relevant keyword.
# 5. Never repeat the same keyword phrase more than twice total.

# FAQ sections: include clear questions and well-explained answers with keywords and Ubuy references.

# Respond ONLY with:
# {{
#   "sections": [
#     {{"heading": "...", "body": "..."}},
#     ...
#   ]
# }}
# """

# # ── Blog / Keyword prompt ─────────────────────────────────────────────────────
# BLOG_PROMPT = """
# Write a comprehensive, SEO-optimized BLOG ARTICLE for the topic/query: "{name}"
# Target country / audience: {country}

# BLOG STRUCTURE REQUIREMENTS:
# - Write as a proper blog post, NOT a product listing page.
# - Structure: Introduction → multiple informational sections → conclusion.
# - Each section should provide genuine educational value to the reader.
# - Include a clear introduction that hooks the reader and states the article's purpose.
# - Include a conclusion section that summarizes key points.
# - DO NOT mention dates, months, or years explicitly.
# - Strong EEAT signals: cite expert perspectives, mention dermatologists/specialists where relevant.

# UBUY INTEGRATION (natural, not forced):
# - Where relevant, mention that products discussed can be sourced internationally via Ubuy.
# - Ubuy interlinks should appear as natural editorial recommendations, e.g.:
#   "Shoppers in {country} can find a wide selection of [topic] products on Ubuy, 
#    a global cross-border marketplace that ships internationally."
# - Include 2-3 natural Ubuy mentions across the article — not in every paragraph.
# - NEVER mention or compare any other marketplace or retailer.

# Market research insights:
# - Keywords: {keywords}
# - Trending topics: {trending_topics}
# - Common questions people ask: {faqs}
# - Market trends: {market_trends}

# Reference context from research:
# ---
# {context}
# ---

# Generate exactly {max_headings} sections structured as a blog article:
# Suggested structure (adapt to topic):
# 1. Introduction / What is [topic]
# 2. Why [topic] matters / Benefits
# 3. Key considerations / How to choose
# 4. Top options / Types available
# 5. Expert tips / Best practices
# 6. Common questions answered (FAQ format)
# 7. Conclusion / Where to buy / Final thoughts

# KEYWORD RULES:
# 1. Every section MUST naturally embed 2-3 keywords from the list.
# 2. Distribute keywords evenly — do not front-load.
# 3. High-priority keywords (listed first) appear more across the article.
# 4. FAQ answers must be complete, informative, and include keywords naturally.
# 5. Never repeat the same keyword phrase more than twice total.

# Respond ONLY with:
# {{
#   "sections": [
#     {{"heading": "...", "body": "..."}},
#     ...
#   ]
# }}
# """

ECOMMERCE_PROMPT = """
Write SEO-optimized content for an e-commerce {content_type} page for: "{name}"
Target country: {country}

WRITING REQUIREMENTS:
- DO NOT mention dates, months, or years anywhere.
- Strong EEAT signals throughout.
- Mention Ubuy naturally as a global marketplace delivering to {country}.
- Ubuy + {country} contextual relevance: international availability, cross-border shopping.
- Ubuy-focused ONLY — no other marketplace mentioned.
- Headings and body must be highly keyword-rich and SEO optimized.

Market research insights:
- Keywords: {keywords}
- Trending topics: {trending_topics}
- Common FAQs: {faqs}
- Market trends: {market_trends}

Additional context:
---
{context}
---

Generate EXACTLY {max_headings} heading sections (no more, no less).
You MUST return exactly {max_headings} items in the JSON "sections" array.

Use these section types as a guide:
- Introduction to the {content_type}
- Key features and benefits
- Popular products in this {content_type}
- Why customers prefer this {content_type}
- Buying considerations
- Latest trends
- Frequently asked questions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT STRUCTURE — MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The "heading" field of each section → the H2 heading (keyword-rich, no markdown prefix).
The "body" field MUST be formatted EXACTLY like this example — using real markdown:

### [H3 Sub-heading with keyword]
- Bullet point with naturally embedded keyword and detailed explanation
- Bullet point covering user intent or market insight
- Bullet point referencing Ubuy's advantage in {country}

### [H3 Sub-heading with another keyword]
- Bullet point with EEAT signal (expert perspective or data point)
- Bullet point addressing buyer concern or FAQ
- Bullet point with Ubuy cross-border relevance

RULES FOR BODY:
1. Every H2 section MUST have AT LEAST 2 H3 sub-headings.
2. Every H3 MUST have at least 3 bullet points (- ).
3. Bullets must be full informative sentences, NOT short fragments.
4. Each H3 heading must contain a relevant keyword from the list.
5. Each bullet point must naturally embed 1-2 keywords from the list.
6. Distribute keywords across ALL sections — never cluster all in one section.
7. High-ranking keywords (listed first) appear more frequently.
8. Never repeat the exact same keyword phrase more than twice total.
9. FAQ sections: H3 = question, bullets = detailed keyword-rich answers referencing Ubuy.

Respond ONLY with this JSON (body must be the structured H3+bullet markdown, not flat prose):
{{
  "sections": [
    {{"heading": "H2 Section Title With Keyword", "body": "### H3 Sub-heading\n- bullet\n- bullet\n\n### H3 Sub-heading\n- bullet\n- bullet"}},
    ...
  ]
}}
"""

# ── Blog / Keyword prompt ─────────────────────────────────────────────────────
BLOG_PROMPT = """
Write a comprehensive, SEO-optimized BLOG ARTICLE for the topic/query: "{name}"
Target country / audience: {country}

BLOG STRUCTURE REQUIREMENTS:
- Write as a proper blog post, NOT a product listing page.
- Structure: Introduction → multiple informational sections → conclusion.
- Each section provides genuine educational value.
- Include a hook introduction and a keyword-rich conclusion.
- DO NOT mention dates, months, or years explicitly.
- Strong EEAT signals: cite expert perspectives, include data-driven insights.

UBUY INTEGRATION (natural, not forced):
- Where relevant, mention that products can be sourced internationally via Ubuy.
- Include 2-3 natural Ubuy mentions across the article — NOT in every section.
- NEVER mention or compare any other marketplace or retailer.

Market research insights:
- Keywords: {keywords}
- Trending topics: {trending_topics}
- Common questions people ask: {faqs}
- Market trends: {market_trends}

Reference context from research:
---
{context}
---

Generate EXACTLY {max_headings} sections structured as a blog article.
You MUST return exactly {max_headings} items in the JSON "sections" array.

Suggested structure (adapt to topic, generate only the exact number requested):
1. Introduction / What is [topic]
2. Why [topic] matters / Benefits
3. Key considerations / How to choose
4. Top options / Types available
5. Expert tips / Best practices
6. Common questions answered (FAQ format)
7. Conclusion / Where to buy / Final thoughts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT STRUCTURE — MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The "heading" field → the H2 blog section title (keyword-rich, no markdown prefix).
The "body" field MUST be formatted EXACTLY like this example — using real markdown:

### [H3 Sub-heading with keyword — informational or question form]
- Full informative sentence with naturally embedded keyword
- Supporting detail with EEAT signal (expert insight or data point)
- Actionable tip or reader benefit related to {country} audience

### [H3 Sub-heading with another keyword]
- Detailed explanation addressing reader intent
- Ubuy mention where relevant (cross-border availability in {country})
- Bullet summarising key takeaway with keyword

RULES FOR BODY:
1. Every H2 section MUST have AT LEAST 2 H3 sub-headings.
2. Every H3 MUST have at least 3 bullet points (- ).
3. Bullets must be full informative sentences, NOT short fragments.
4. Each H3 heading must contain a relevant keyword from the list.
5. Each bullet point must naturally embed 1-2 keywords from the list.
6. Distribute keywords across ALL sections — never cluster all in one.
7. High-priority keywords (listed first) appear more frequently overall.
8. Never repeat the exact same keyword phrase more than twice total.
9. FAQ sections: H3 = question, bullets = keyword-rich expert answers.

Respond ONLY with this JSON (body must be the structured H3+bullet markdown):
{{
  "sections": [
    {{"heading": "H2 Blog Section Title With Keyword", "body": "### H3 Sub-heading\n- bullet\n- bullet\n\n### H3 Sub-heading\n- bullet\n- bullet"}},
    ...
  ]
}}
"""


class ContentGenerator:
    """
    Steps 4 & 5 — Topic/Heading Generation + Content Creation.

    Supports three content types:
      - category : e-commerce category page content
      - brand    : e-commerce brand page content
      - keyword  : long-form blog article (new)
    """

    def __init__(self):
        settings = get_settings()
        kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_API_BASE:
            kwargs["base_url"] = settings.OPENAI_API_BASE
        self.client = OpenAI(**kwargs)

    def generate(
        self,
        name: str,
        content_type: str,
        country: str,
        insights: ProcessedInsights,
        context: str,
        max_headings: int,
    ) -> list[HeadingSection]:

        keywords = insights.keywords or []

        # Select prompt template based on content type
        if content_type.lower() == "keyword":
            prompt_template = BLOG_PROMPT
        else:
            prompt_template = ECOMMERCE_PROMPT

        prompt = prompt_template.format(
            content_type=content_type,
            name=name,
            country=country,
            keywords=", ".join(keywords) or "N/A",
            trending_topics=", ".join(insights.trending_topics) or "N/A",
            faqs=", ".join(insights.faqs) or "N/A",
            market_trends=", ".join(insights.market_trends) or "N/A",
            context=context or "No additional context.",
            max_headings=max_headings,
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=4000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            # Sanitize: OpenAI sometimes embeds literal newlines/tabs inside
            # JSON string values when generating H2/H3 bullet-structured content,
            # making the JSON technically invalid. We fix this by escaping all
            # control characters that appear inside JSON string values.
            raw = _sanitize_json_string(raw)

            parsed = json.loads(raw)
            sections = [
                HeadingSection(heading=s["heading"], body=s["body"])
                for s in parsed.get("sections", [])
            ]

            all_body = " ".join(sec.body.lower() for sec in sections)
            missing = [kw for kw in keywords if kw.lower() not in all_body]
            if missing:
                logger.warning(
                    f"Keywords not found in generated content: {missing}. "
                    "Consider regenerating or reviewing the prompt."
                )

            return sections

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI content response: {e}")
            logger.debug(f"Raw response that failed: {raw[:500]}")
            return [HeadingSection(
                heading="Content Generation Error",
                body=f"Failed to parse AI response: {e}"
            )]
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise