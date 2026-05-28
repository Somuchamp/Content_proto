import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Content Generator Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = "http://127.0.0.1:8800/api/content"

st.markdown("""
<style>
    div[data-testid="stForm"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
    }
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(#60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle { color: #94a3b8; font-size: 1.1rem; margin-bottom: 2rem; }
    div[data-testid="stMetricValue"] { color: #38bdf8; }
    hr { border-color: #334155; }
    .pas-tag {
        display: inline-block;
        background-color: #1e3a5f;
        border: 1px solid #2563eb;
        color: #93c5fd;
        border-radius: 20px;
        padding: 3px 12px;
        margin: 3px 4px;
        font-size: 0.82rem;
        font-family: monospace;
    }
    .product-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        height: 100%;
    }
    .product-card img { border-radius: 6px; width: 100%; max-height: 120px; object-fit: contain; }
    .product-price { color: #4ade80; font-weight: bold; font-size: 1.1rem; }
    .product-source { color: #94a3b8; font-size: 0.8rem; }
    .video-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 8px;
        margin-bottom: 10px;
    }
    .ai-overview-block {
        background: #1e293b;
        border-left: 3px solid #6366f1;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
        color: #cbd5e1;
        font-size: 0.9rem;
    }
    .ai-ref {
        background: #0f172a;
        border: 1px solid #1e3a5f;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 0.85rem;
    }
    .diff-easy   { color: #4ade80; font-weight: bold; }
    .diff-medium { color: #facc15; font-weight: bold; }
    .diff-hard   { color: #f87171; font-weight: bold; }
    .blog-badge {
        background: #7c3aed;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def format_date(date_str):
    if not date_str:
        return "N/A"
    try:
        return datetime.fromisoformat(date_str).strftime("%B %d, %Y at %I:%M %p")
    except:
        return date_str


def difficulty_label(score: int) -> str:
    if score <= 35:
        return f"<span class='diff-easy'>{score} Easy</span>"
    elif score <= 65:
        return f"<span class='diff-medium'>{score} Medium</span>"
    else:
        return f"<span class='diff-hard'>{score} Hard</span>"


def render_refine_searches(refine_searches: list):
    """
    Render refine_this_search chips as clickable interlinks.
    Completely separate section from keywords — these are Google's
    shopping filter suggestions with direct Google search links.
    """
    if not refine_searches:
        return
    st.markdown("### 🔖 Refine This Search")
    st.caption("Google's shopping filter suggestions — click any to open the refined Google search.")
    chips_html = ""
    for item in refine_searches:
        if isinstance(item, dict):
            query = item.get("query", "")
            link  = item.get("link", "")
            if query and link:
                chips_html += (
                    f"<a href='{link}' target='_blank' style='"
                    f"display:inline-block;background:#1e3a5f;border:1px solid #2563eb;"
                    f"color:#93c5fd;border-radius:20px;padding:4px 14px;margin:3px 4px;"
                    f"font-size:0.82rem;font-family:monospace;text-decoration:none;"
                    f"'>🔖 {query}</a>"
                )
            elif query:
                chips_html += (
                    f"<span style='display:inline-block;background:#1e293b;border:1px solid #334155;"
                    f"color:#94a3b8;border-radius:20px;padding:4px 14px;margin:3px 4px;"
                    f"font-size:0.82rem;font-family:monospace;'>{query}</span>"
                )
    if chips_html:
        st.markdown(chips_html, unsafe_allow_html=True)
    st.markdown("---")


def render_immersive_products(products: list, more_products: list = None):
    """
    Render Google Shopping products grid.
    Popular products shown inline.
    More products shown only when user clicks the expand button.
    """
    popular = [p for p in (products or []) if isinstance(p, dict) and "popular" in p.get("category", "").lower()]
    more    = more_products or []

    if not popular and not more:
        return

    def _product_grid(items):
        cols_per_row = 4
        for i in range(0, len(items), cols_per_row):
            chunk = items[i:i + cols_per_row]
            cols = st.columns(len(chunk))
            for col, prod in zip(cols, chunk):
                with col:
                    thumb   = prod.get("thumbnail", "")
                    title   = prod.get("title", "Unknown")
                    source  = prod.get("source", "")
                    price   = prod.get("price", "")
                    rating  = prod.get("rating")
                    reviews = prod.get("reviews")
                    if thumb:
                        st.image(thumb, use_column_width=True)
                    st.markdown(f"**{title[:50]}{'...' if len(title)>50 else ''}**")
                    if price:
                        st.markdown(f"<span class='product-price'>{price}</span>", unsafe_allow_html=True)
                    if source:
                        st.markdown(f"<span class='product-source'>📦 {source}</span>", unsafe_allow_html=True)
                    if rating:
                        stars = "⭐" * int(round(rating))
                        rev_text = f"({reviews:,})" if reviews else ""
                        st.caption(f"{stars} {rating} {rev_text}")

    if popular:
        st.markdown("### 🛒 Popular Products (Google Shopping Grid)")
        st.caption("Products surfaced in Google's immersive shopping carousel for this query.")
        _product_grid(popular)

    if more:
        if st.button(f"🛍️ Show More Products ({len(more)})", key="more_products_btn"):
            st.markdown("#### 🛍️ More Products")
            _product_grid(more)

    st.markdown("---")


def render_inline_videos(videos: list, more_videos: list = None):
    """
    Render inline video results from SERP.
    Top videos shown inline; more videos shown on button click.
    """
    inline = videos or []
    more   = more_videos or []

    if not inline and not more:
        return

    def _video_row(items, max_cols=3):
        cols = st.columns(min(len(items), max_cols))
        for col, vid in zip(cols, items[:max_cols]):
            with col:
                thumb    = vid.get("thumbnail", "")
                title    = vid.get("title", "")
                link     = vid.get("link", "")
                channel  = vid.get("channel", "")
                platform = vid.get("platform", "")
                duration = vid.get("duration", "")
                date     = vid.get("date", "")
                if thumb:
                    st.image(thumb, use_column_width=True)
                if link and title:
                    st.markdown(f"[**{title[:55]}{'...' if len(title)>55 else ''}**]({link})")
                elif title:
                    st.markdown(f"**{title}**")
                meta = " · ".join(filter(None, [channel, platform, duration, date]))
                if meta:
                    st.caption(f"📺 {meta}")

    if inline:
        st.markdown("### 🎬 Inline Videos (Google SERP)")
        st.caption("Videos Google surfaces inline for this query.")
        _video_row(inline, max_cols=3)

    if more:
        if st.button(f"▶️ Show More Videos ({len(more)})", key="more_videos_btn"):
            st.markdown("#### ▶️ More Videos")
            # Show in rows of 3
            for i in range(0, len(more), 3):
                _video_row(more[i:i+3], max_cols=3)

    st.markdown("---")


def render_ai_overview(text_blocks: list, references: list):
    """Render Google AI Overview section."""
    if not text_blocks and not references:
        return

    st.markdown("### 🤖 Google AI Overview")
    st.caption("AI-generated summary from Google's AI Overview feature for this query.")

    if text_blocks:
        for block in text_blocks:
            st.markdown(f"<div class='ai-overview-block'>{block}</div>", unsafe_allow_html=True)

    if references:
        st.markdown("**📚 AI Overview References:**")
        for ref in references[:6]:
            title   = ref.get("title", "")
            link    = ref.get("link", "")
            snippet = ref.get("snippet", "")[:120]
            source  = ref.get("source", "")
            if link and title:
                st.markdown(
                    f"<div class='ai-ref'>🔗 <a href='{link}' target='_blank'><b>{title[:70]}</b></a>"
                    f"<br><span style='color:#94a3b8;font-size:0.8rem;'>{source}</span>"
                    f"<br><span style='color:#64748b;'>{snippet}{'...' if snippet else ''}</span></div>",
                    unsafe_allow_html=True
                )
    st.markdown("---")


def render_content_details(content):
    ct = content.get("content_type", "category")
    badge = ""
    if ct == "keyword":
        badge = " <span class='blog-badge'>BLOG</span>"
    st.markdown(f"### 📋 {content['name']}{badge}", unsafe_allow_html=True)

    cols = st.columns(4)
    cols[0].write(f"**🏷️ Type:** {ct.capitalize()}")
    cols[1].write(f"**🌍 Region:** {content['country']}")
    cols[2].write(f"**🕒 Generated:** {format_date(content['created_at'])}")
    cols[3].write(f"**🔄 Refresh:** {content['refresh_interval'].capitalize()}")

    st.markdown("<br>", unsafe_allow_html=True)

    sections = content.get("sections", [])
    full_article_text = ""
    for idx, sec in enumerate(sections, 1):
        full_article_text += f"## {idx}. {sec['heading']}\n\n{sec.get('body', '')}\n\n"

    export_cols = st.columns([1, 1, 1.2, 2.8])

    json_data = json.dumps(content, indent=2)
    export_cols[0].download_button(
        label="📥 Download JSON", data=json_data,
        file_name=f"{content['name'].replace(' ','_').lower()}_{content['id'][:8]}.json",
        mime="application/json", use_container_width=True
    )

    insights = content.get("insights", {})

    csv_rows = []
    for s in sections:
        csv_rows.append({"Category": "Section", "Heading/Type": s["heading"], "Value": s["body"][:100]+"..."})
    for kw in insights.get("keywords", []):
        csv_rows.append({"Category": "Keyword", "Heading/Type": "SEO Keyword", "Value": kw})
    for term in insights.get("people_also_search_for", []):
        csv_rows.append({"Category": "SERP", "Heading/Type": "People Also Search For", "Value": term})
    for q in insights.get("people_also_ask", []):
        csv_rows.append({"Category": "SERP", "Heading/Type": "People Also Ask", "Value": q})
    for p in insights.get("immersive_products", []):
        if isinstance(p, dict):
            csv_rows.append({"Category": "Shopping", "Heading/Type": "Popular Product", "Value": p.get("title","")})
    for v in insights.get("inline_videos", []):
        if isinstance(v, dict):
            csv_rows.append({"Category": "Video", "Heading/Type": "Inline Video", "Value": v.get("title","")})

    if csv_rows:
        csv_df = pd.DataFrame(csv_rows)
        export_cols[1].download_button(
            label="📊 Download CSV", data=csv_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{content['name'].replace(' ','_').lower()}_{content['id'][:8]}.csv",
            mime="text/csv", use_container_width=True
        )

    with export_cols[2]:
        with st.expander("📋 Copy Full Article"):
            st.code(full_article_text, language="markdown")

    st.markdown("---")

    # ── Metrics row ────────────────────────────────────────────────────────────
    st.markdown("#### 🎯 Extraction Metrics")
    m1, m2, m3, m4, m5, m6, m7, m8, m9 = st.columns(9)
    m1.metric("Keywords",         len(insights.get("keywords", [])))
    m2.metric("Autocomplete",     len(insights.get("autocomplete_keywords", [])))
    m3.metric("People Also Ask",  len(insights.get("people_also_ask", [])))
    m4.metric("People Search",    len(insights.get("people_also_search_for", [])))
    m5.metric("Reddit Trends",    len(insights.get("reddit_trends", [])))
    m6.metric("YouTube Signals",  len(insights.get("youtube_trends", [])))
    m7.metric("FAQs",             len(insights.get("faqs", [])))
    popular_count = len(insights.get("immersive_products", []))
    more_count    = len(insights.get("more_products", []))
    m8.metric("🛒 Products",      f"{popular_count}+{more_count}")
    m9.metric("Sections",         len(sections))

    # ── People Also Search For ─────────────────────────────────────────────────
    pas = insights.get("people_also_search_for", [])
    if pas:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🔍 People Also Search For")
        tags_html = "".join([f"<span class='pas-tag'>🔎 {term}</span>" for term in pas])
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Refine This Search — separate from keywords ──────────────────────────
    render_refine_searches(insights.get("refine_searches", []))

    # ── Google Shopping Products Grid (Popular + More on button) ─────────────
    render_immersive_products(
        insights.get("immersive_products", []),
        insights.get("more_products", []),
    )

    # ── Inline Videos + More Videos on button ────────────────────────────────
    render_inline_videos(
        insights.get("inline_videos", []),
        insights.get("more_videos", []),
    )

    # ── AI Overview ──────────────────────────────────────────────────────────
    render_ai_overview(
        insights.get("ai_overview_text", []),
        insights.get("ai_overview_references", [])
    )

    # ── Two-column layout ─────────────────────────────────────────────────────
    left_col, right_col = st.columns([2, 1])

    with left_col:
        if ct == "keyword":
            st.markdown("#### 📝 Blog Article Sections")
            st.caption("Blog-structured content with Ubuy interlinks — ready for publishing.")
        else:
            st.markdown("#### ✍️ Generated Article Sections")

        if not sections:
            st.info("No content sections available.")
        for idx, sec in enumerate(sections, 1):
            render_structured_section(sec["heading"], sec["body"], idx)

    with right_col:
        st.markdown("#### 🧠 Market & SEO Insights")

        tabs = st.tabs([
            "🔑 Keywords",
            "🔮 Autocomplete",
            "❓ People Also Ask",
            "🔍 People Search",
            "💬 Reddit",
            "▶️ YouTube",
            "📦 Clusters",
            "📊 Difficulty",
            "📈 Trends",
            "🙋 FAQs",
        ])

        with tabs[0]:
            kws = insights.get("keywords", [])
            if kws:
                for kw in kws:
                    st.markdown(f"✨ `{kw}`")
            else:
                st.caption("No keywords found.")

        with tabs[1]:
            auto = insights.get("autocomplete_keywords", [])
            if auto:
                for kw in auto:
                    st.markdown(f"🔎 `{kw}`")
            else:
                st.caption("No autocomplete suggestions.")

        with tabs[2]:
            paa = insights.get("people_also_ask", [])
            if paa:
                for q in paa:
                    st.info(q)
            else:
                st.caption("No PAA questions found.")

        with tabs[3]:
            if pas:
                for term in pas:
                    st.markdown(f"🔎 `{term}`")
            else:
                st.caption("No 'People Also Search For' data.")

        with tabs[4]:
            reddit = insights.get("reddit_trends", [])
            if reddit:
                st.caption("Phrases trending in Reddit discussions related to this topic.")
                for r in reddit:
                    st.success(r)
            else:
                st.caption("No Reddit trends detected.")

        with tabs[5]:
            yt_items = insights.get("youtube_trends", [])
            if yt_items:
                st.caption("YouTube videos relevant to this category (title + link).")
                for yt in yt_items:
                    if isinstance(yt, dict):
                        title = yt.get("title", "")
                        url   = yt.get("url", "")
                        st.markdown(f"▶️ [{title}]({url})" if url else f"▶️ {title}")
                    else:
                        st.markdown(f"▶️ {yt}")
            else:
                st.caption("No YouTube signals found.")

        with tabs[6]:
            clusters = insights.get("keyword_clusters", [])
            if clusters:
                for idx, cluster in enumerate(clusters, 1):
                    if len(cluster) > 1:
                        st.markdown(f"**Cluster {idx}** ({len(cluster)} keywords)")
                        for kw in cluster:
                            st.markdown(f"- `{kw}`")
            else:
                st.caption("No clusters generated.")

        with tabs[7]:
            difficulty = insights.get("keyword_difficulty", {})
            if difficulty:
                for kw, score in sorted(difficulty.items(), key=lambda x: -x[1]):
                    label = difficulty_label(score)
                    st.markdown(f"`{kw}` — {label}", unsafe_allow_html=True)
            else:
                st.caption("No difficulty scores.")

        with tabs[8]:
            topics = insights.get("trending_topics", [])
            market = insights.get("market_trends", [])
            if topics:
                st.markdown("**📈 Trending Topics**")
                for t in topics:
                    st.success(t)
            if market:
                st.markdown("**🏪 Market Trends**")
                for t in market:
                    st.info(t)
            if not topics and not market:
                st.caption("No trend data.")

        with tabs[9]:
            faqs = insights.get("faqs", [])
            if faqs:
                for faq in faqs:
                    st.info(faq)
            else:
                st.caption("No FAQs found.")

        # ── Data Sources — grouped by platform ───────────────────────────────
        st.markdown("#### 🌐 Data Sources")
        sources = content.get("source_urls", [])
        if sources:
            def _platform(u):
                if "youtube" in u or "youtu.be" in u: return "youtube"
                if "reddit" in u:                      return "reddit"
                if "quora" in u or "medium" in u:      return "blog/forum"
                return "serp"

            grouped = {"serp": [], "youtube": [], "reddit": [], "blog/forum": []}
            for url in sources:
                grouped[_platform(url)].append(url)

            icons = {"serp": "🔍", "youtube": "▶️", "reddit": "💬", "blog/forum": "📝"}
            for platform, urls in grouped.items():
                if not urls:
                    continue
                st.caption(f"{icons[platform]} **{platform.upper()}** ({len(urls)})")
                for url in urls[:10]:
                    label = url[:55] + "..." if len(url) > 55 else url
                    st.markdown(f"&nbsp;&nbsp;🔗 [{label}]({url})", unsafe_allow_html=True)
        else:
            st.caption("No sources tracked.")




def fmt_num(val) -> str:
    try:
        n = int(val)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        elif n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)
    except (TypeError, ValueError):
        return str(val) if val else "—"


def render_structured_section(heading: str, body: str, idx: int):
    """Render a content section with structured H2/H3/bullet markdown body."""
    st.markdown(
        f"<div style='font-size:1.35rem;font-weight:700;color:#60a5fa;"
        f"border-left:4px solid #3b82f6;padding-left:12px;margin:1.4rem 0 0.5rem 0;'>"
        f"## {idx}. {heading}</div>",
        unsafe_allow_html=True
    )
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            h3 = stripped[4:].strip()
            st.markdown(
                f"<div style='font-size:1.05rem;font-weight:600;color:#a78bfa;"
                f"margin:0.8rem 0 0.3rem 0.5rem;'>▸ {h3}</div>",
                unsafe_allow_html=True
            )
        elif stripped.startswith("- ") or stripped.startswith("• "):
            bullet = stripped[2:].strip()
            st.markdown(
                f"<div style='color:#cbd5e1;line-height:1.7;margin:0.15rem 0 0.15rem 1.5rem;"
                f"font-size:0.93rem;'>◦ {bullet}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(stripped)
    with st.expander(f"📋 Copy Section {idx}"):
        st.code(f"## {heading}\n\n{body}", language="markdown")
    st.markdown("<hr style='border-color:#1e293b;margin:1rem 0;'>", unsafe_allow_html=True)


def page_generate():
    st.markdown("<h1>✨ Studio Pipeline</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Configure and execute the AI-driven research and content generation pipeline.</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["🚀 Standard Research", "🔗 From URLs"])

    with tab1:
        with st.form("generate_form"):
            st.markdown("### 📝 Configuration")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Target Keyword / Product Name / Blog Query",
                    placeholder="e.g. Mechanical Keyboards  |  best skin care routine  |  Sony WH-1000XM5"
                )
                content_type = st.selectbox(
                    "Content Strategy",
                    options=["category", "brand", "keyword"],
                    format_func=lambda x: {
                        "category": "📂 Category Page",
                        "brand":    "🏷️ Brand Page",
                        "keyword":  "📝 Blog / Keyword Article",
                    }[x],
                    help=(
                        "Category → e-commerce category page content\n"
                        "Brand → brand-specific page content\n"
                        "Keyword/Query → long-form blog article with Ubuy interlinks"
                    )
                )
                country = st.text_input(
                    "Target Regional Search (Country)", value="United States"
                )

            with col2:
                max_headings     = st.slider("Depth (Number of Sections)", min_value=1, max_value=15, value=7)
                refresh_interval = st.selectbox(
                    "Pipeline Automation", options=["daily", "weekly", "monthly", "custom"]
                )
                custom_hours = None
                if refresh_interval == "custom":
                    custom_hours = st.number_input("Custom Refresh Rate (Hours)", min_value=1, value=24)

                # Contextual hint for the selected content type
                if content_type == "keyword":
                    st.info(
                        "📝 **Blog Mode**: Generates a long-form blog article structured with "
                        "introduction, informational sections, FAQ, and conclusion. "
                        "Includes natural Ubuy interlinks for the target country."
                    )
                elif content_type == "brand":
                    st.info("🏷️ **Brand Mode**: Optimized for brand page SEO with product highlights.")
                else:
                    st.info("📂 **Category Mode**: Optimized for e-commerce category page SEO.")

            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 Generate Content", use_container_width=True)

            if submitted:
                if not name or not country:
                    st.error("⚠️ Please provide both the Target Keyword and Country.")
                    st.stop()

                payload = {
                    "name": name, "content_type": content_type,
                    "country": country, "max_headings": max_headings,
                    "refresh_interval": refresh_interval
                }
                if custom_hours:
                    payload["custom_interval_hours"] = custom_hours

                spinner_msg = {
                    "keyword":  "📝 Researching blog topic, mining PAA, keywords & trends...",
                    "brand":    "🏷️ Analyzing brand SERP, reviews & product data...",
                    "category": "📂 Analyzing SERP, YouTube, Reddit & Forums...",
                }.get(content_type, "🤖 Running pipeline...")

                with st.spinner(spinner_msg):
                    try:
                        res = requests.post(f"{API_BASE_URL}/generate", json=payload, timeout=600)
                        if res.status_code == 201:
                            st.success("🎉 Content synthesized and saved successfully!")
                            st.session_state["generated_data"] = res.json()
                        else:
                            st.error(f"❌ Pipeline failed: {res.text}")
                    except Exception as e:
                        st.error(f"🔌 Connection error: {e}")

    with tab2:
        with st.form("url_generate_form"):
            st.markdown("### 📝 Provide Source URLs")
            st.info("Paste up to 200 URLs (one per line). AI extracts context from these pages.")
            urls_text = st.text_area("Source URLs", height=200, placeholder="https://medium.com/...")

            st.markdown("### 📝 Metadata")
            uc1, uc2 = st.columns(2)
            with uc1:
                url_name = st.text_input("Target Keyword / Product Name ")
                url_content_type = st.selectbox(
                    "Content Strategy ",
                    options=["category", "brand", "keyword"],
                    format_func=lambda x: {
                        "category": "📂 Category Page",
                        "brand":    "🏷️ Brand Page",
                        "keyword":  "📝 Blog / Keyword Article",
                    }[x]
                )
            with uc2:
                url_country      = st.text_input("Target Regional Search (Country) ", value="United States")
                url_max_headings = st.slider("Depth (Number of Sections) ", min_value=1, max_value=15, value=7)

            st.markdown("<br>", unsafe_allow_html=True)
            url_submitted = st.form_submit_button("🚀 Generate from URLs", use_container_width=True)

            if url_submitted:
                urls = [u.strip() for u in urls_text.split("\n") if u.strip().startswith("http")]
                if not urls:
                    st.error("⚠️ Provide at least one valid URL.")
                elif len(urls) > 200:
                    st.error("⚠️ Maximum 200 URLs.")
                elif not url_name or not url_country:
                    st.error("⚠️ Please provide both the Target Keyword and Country.")
                else:
                    payload = {
                        "urls": urls, "name": url_name,
                        "content_type": url_content_type,
                        "country": url_country, "max_headings": url_max_headings,
                    }
                    with st.spinner(f"🤖 Scraping {len(urls)} URLs and synthesizing..."):
                        try:
                            res = requests.post(f"{API_BASE_URL}/generate-from-urls", json=payload, timeout=900)
                            if res.status_code == 201:
                                st.success("🎉 Content synthesized and saved successfully!")
                                st.session_state["generated_data"] = res.json()
                            else:
                                st.error(f"❌ Pipeline failed: {res.text}")
                        except Exception as e:
                            st.error(f"🔌 Connection error: {e}")

    if "generated_data" in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        render_content_details(st.session_state["generated_data"])


def page_view_existing():
    st.markdown("<h1>📚 Content Library</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Browse your portfolio of SEO-optimized articles and research reports.</p>",
        unsafe_allow_html=True
    )

    try:
        res = requests.get(f"{API_BASE_URL}/")
        if res.status_code != 200:
            st.error(f"Failed to fetch content list: {res.text}")
            return

        contents = res.json()
        if not contents:
            st.info("Library is empty. Head to Studio Pipeline to generate content!")
            return

        df_data = [{
            "ID":           c["id"],
            "Keyword/Title":c["name"],
            "Type":         c["content_type"].capitalize(),
            "Region":       c["country"],
            "Created":      format_date(c["created_at"]),
            "Auto-Refresh": c["refresh_interval"].capitalize()
        } for c in contents]

        df = pd.DataFrame(df_data)

        tc1, tc2 = st.columns(2)
        tc1.metric("Total Documents", len(df))
        tc2.metric("Most Recent",
                   df.sort_values("Created", ascending=False).iloc[0]["Keyword/Title"]
                   if not df.empty else "N/A")

        st.markdown("### 📂 Archive")
        selected_id = st.selectbox(
            "Select a report to analyze:",
            options=df["ID"].tolist(),
            format_func=lambda x: f"{df[df['ID']==x]['Keyword/Title'].values[0]} ({x[:8]})"
        )
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

        if selected_id:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.spinner("Loading document insights..."):
                dr = requests.get(f"{API_BASE_URL}/{selected_id}")
                if dr.status_code == 200:
                    st.markdown("---")
                    render_content_details(dr.json())
                else:
                    st.error("Failed to fetch document details.")

    except Exception as e:
        st.error(f"Error connecting to backend: {e}")


def page_automations():
    st.markdown("<h1>⚙️ Automation Management</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>View and control your active background research schedules.</p>",
        unsafe_allow_html=True
    )

    API_SCHEDULER_URL = "http://127.0.0.1:8800/api/scheduler"

    try:
        res = requests.get(f"{API_SCHEDULER_URL}/jobs")
        if res.status_code != 200:
            st.error("Failed to fetch jobs from API.")
            return

        jobs = res.json().get("jobs", [])
        if not jobs:
            st.info("No active automations running.")
            return

        st.write(f"**Active Jobs:** {len(jobs)}")
        for idx, job in enumerate(jobs):
            job_id     = job.get("job_id", "")
            content_id = job_id.replace("refresh_", "") if job_id.startswith("refresh_") else job_id
            st.markdown(f"### Job: `{job_id}`")
            jc1, jc2, jc3 = st.columns(3)
            jc1.write(f"**Content ID:** {content_id}")
            jc2.write("**Interval:** Custom/Unknown")
            jc3.write(f"**Next Run:** {format_date(job.get('next_run_at'))}")

            col_mod, col_can = st.columns(2)
            with col_mod:
                with st.expander("Modify Schedule"):
                    new_interval = st.selectbox(
                        "New Interval", ["daily", "weekly", "monthly", "custom"], key=f"int_{idx}"
                    )
                    custom_h = None
                    if new_interval == "custom":
                        custom_h = st.number_input("Custom Hours", min_value=1, value=24, key=f"cust_{idx}")
                    if st.button("Update Schedule", key=f"updc_{idx}"):
                        payload = {"content_id": content_id, "refresh_interval": new_interval}
                        if custom_h:
                            payload["custom_interval_hours"] = custom_h
                        upd = requests.post(f"{API_SCHEDULER_URL}/set", json=payload)
                        st.success("Updated!") if upd.status_code == 200 else st.error(upd.text)
            with col_can:
                if st.button("Cancel Automation", type="primary", key=f"canc_{idx}"):
                    dr = requests.delete(f"{API_SCHEDULER_URL}/cancel/{content_id}")
                    st.success("Cancelled!") if dr.status_code == 200 else st.error("Failed.")
            st.markdown("---")

    except Exception as e:
        st.error(f"Connection error: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# DEEP RESEARCH PAGE
# ═════════════════════════════════════════════════════════════════════════════

def page_deep_research():
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    try:
        from app.services import dataforseo_service as ah
    except ImportError:
        st.error("❌ DataForSEO service module not found. Ensure app/services/dataforseo_service.py exists.")
        return

    st.markdown("<h1>🔬 Deep Research</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Full DataForSEO-powered SEO intelligence — keywords, rankings, content ideas, site analysis & audits.</p>",
        unsafe_allow_html=True
    )

    gi1, gi2, gi3 = st.columns([2, 2, 1])
    with gi1:
        dr_keyword = st.text_input("🔍 Target Keyword", placeholder="e.g. mechanical keyboards", key="dr_kw")
    with gi2:
        dr_url = st.text_input("🌐 Target Domain / URL", placeholder="e.g. example.com", key="dr_url")
    with gi3:
        dr_country = st.selectbox("🌍 Country", options=list(ah.COUNTRY_CODES.keys()), index=0, key="dr_country")

    if not dr_keyword and not dr_url:
        st.info("Enter a keyword and/or domain above to start researching.")
        return

    st.markdown("---")
    tab_kw, tab_rank, tab_content, tab_site = st.tabs([
        "🔍 Keyword Explorer", "📈 Rank Tracker", "📝 Content Explorer",
        "🌐 Site Explorer"
    ])

    def _metric_card(col, label, val):
        col.markdown(
            f"<div style='background:#0f172a;border:1px solid #334155;border-radius:8px;"
            f"padding:10px;text-align:center;'>"
            f"<div style='font-size:1.4rem;font-weight:700;color:#38bdf8;'>{fmt_num(val)}</div>"
            f"<div style='font-size:0.75rem;color:#64748b;margin-top:2px;'>{label}</div>"
            f"</div>", unsafe_allow_html=True
        )

    # ── Keyword Explorer ─────────────────────────────────────────────────────
    with tab_kw:
        st.markdown("### 🔍 Keyword Explorer")
        st.caption(
            "Discover keyword ideas with volume, difficulty and CPC — DataForSEO plus optional "
            "**Google Ads Keyword Planner** when credentials are configured."
        )
        if not dr_keyword:
            st.info("Enter a keyword above.")
        else:
            if st.button("🚀 Fetch Keyword Data", key="btn_kw"):
                with st.spinner(f"Fetching keyword data for **{dr_keyword}** ({dr_country})..."):
                    st.session_state["dr_kw_data"] = {
                        "overview": ah.keyword_overview(dr_keyword, dr_country),
                        "ideas":    ah.keyword_ideas(dr_keyword, dr_country, limit=100),
                        "also":     ah.keyword_also_rank_for(dr_keyword, dr_country, limit=50),
                        "suggest":  ah.keyword_search_suggestions(dr_keyword, dr_country, limit=50),
                        "planner":  {"ideas": [], "error": None},
                    }
                    try:
                        from app.services.google_ads_keyword_planner import (
                            fetch_keyword_planner_ideas,
                            is_google_ads_planner_configured,
                        )
                        if is_google_ads_planner_configured():
                            prow, perr = fetch_keyword_planner_ideas(
                                dr_keyword, dr_country, dr_url or None, limit=100
                            )
                            st.session_state["dr_kw_data"]["planner"] = {
                                "ideas": prow or [],
                                "error": perr,
                            }
                    except ImportError:
                        st.session_state["dr_kw_data"]["planner"] = {
                            "ideas": [],
                            "error": "google-ads package not installed (pip install google-ads).",
                        }

            kd = st.session_state.get("dr_kw_data", {})
            if kd:
                ov = kd.get("overview", {})
                if ov and "error" not in ov:
                    metrics = ov
                    for nk in ("metrics", "data", "overview"):
                        if nk in ov:
                            metrics = ov[nk]
                            break
                    st.markdown("#### 📊 Keyword Overview")
                    mc1, mc2, mc4, mc5 = st.columns(4)
                    _metric_card(mc1, "Search Volume",    metrics.get("volume", "—"))
                    _metric_card(mc2, "Keyword Difficulty", metrics.get("difficulty", "—"))
                    _metric_card(mc4, "CPC (USD)",        metrics.get("cpc", "—"))
                    _metric_card(mc5, "Global Volume",    metrics.get("global_volume", "—"))
                    if metrics.get("parent_topic"):
                        st.caption(f"**Parent Topic:** `{metrics['parent_topic']}`")
                elif ov.get("error"):
                    st.warning(f"Overview: {ov['error']} — {ov.get('detail', '')}")

                def _norm(items, lbl):
                    out = []
                    for item in items:
                        if isinstance(item, dict):
                            vol_raw = item.get("volume", "—")
                            if vol_raw in (None, "", 0):
                                vol_disp = "—"
                            else:
                                vol_disp = fmt_num(vol_raw)
                            cpc_raw = item.get("cpc", "—")
                            if cpc_raw is None or cpc_raw == "":
                                cpc_disp = "—"
                            elif isinstance(cpc_raw, (int, float)) and float(cpc_raw) > 0:
                                cpc_disp = f"{float(cpc_raw):.2f}"
                            else:
                                cpc_disp = str(cpc_raw) if cpc_raw != "—" else "—"
                            out.append({
                                "Keyword": item.get("keyword", ""),
                                "Volume":  vol_disp,
                                "KD":      item.get("difficulty", "—"),
                                "CPC ($)": cpc_disp,
                                "Source":  lbl,
                            })
                        elif isinstance(item, str):
                            out.append({"Keyword": item, "Volume": "—", "KD": "—",
                                        "CPC ($)": "—", "Source": lbl})
                    return out

                def _merge_keyword_rows(rows):
                    """Merge duplicate keywords; prefer Google Ads Planner metrics when overlapping."""
                    merged = []
                    by_key = {}
                    for r in rows:
                        k = (r.get("Keyword") or "").strip().lower()
                        if not k:
                            continue
                        is_planner = "Google Ads Planner" in (r.get("Source") or "")
                        if k not in by_key:
                            by_key[k] = len(merged)
                            merged.append(dict(r))
                            continue
                        i = by_key[k]
                        cur = merged[i]
                        new_src = r.get("Source") or ""
                        if new_src and new_src not in (cur.get("Source") or ""):
                            cur["Source"] = f"{cur['Source']} · {new_src}"
                        if is_planner:
                            if r.get("Volume") not in (None, "", "—"):
                                cur["Volume"] = r["Volume"]
                            if r.get("KD") not in (None, "", "—"):
                                cur["KD"] = r["KD"]
                            if r.get("CPC ($)") not in (None, "", "—"):
                                cur["CPC ($)"] = r["CPC ($)"]
                        else:
                            if cur.get("Volume") in (None, "", "—") and r.get("Volume") not in (None, "", "—"):
                                cur["Volume"] = r["Volume"]
                            if cur.get("KD") in (None, "", "—") and r.get("KD") not in (None, "", "—"):
                                cur["KD"] = r["KD"]
                            if cur.get("CPC ($)") in (None, "", "—") and r.get("CPC ($)") not in (None, "", "—"):
                                cur["CPC ($)"] = r["CPC ($)"]
                    return merged

                all_kws = (
                    _norm(kd.get("ideas", []),   "Phrase Match") +
                    _norm(kd.get("also", []),    "Also Rank For") +
                    _norm(kd.get("suggest", []), "Search Suggestions")
                )
                planner_block = kd.get("planner") or {}
                if planner_block.get("error"):
                    st.warning(f"Google Ads Keyword Planner: {planner_block['error']}")
                if planner_block.get("ideas"):
                    all_kws += _norm(planner_block["ideas"], "Google Ads Planner")
                else:
                    try:
                        from app.services.google_ads_keyword_planner import is_google_ads_planner_configured
                        if not is_google_ads_planner_configured():
                            with st.expander("Optional: Google Ads Keyword Planner", expanded=False):
                                st.markdown(
                                    "Set **GOOGLE_ADS_DEVELOPER_TOKEN**, **GOOGLE_ADS_CLIENT_ID**, "
                                    "**GOOGLE_ADS_CLIENT_SECRET**, **GOOGLE_ADS_REFRESH_TOKEN**, "
                                    "**GOOGLE_ADS_CUSTOMER_ID** (and optional **GOOGLE_ADS_LOGIN_CUSTOMER_ID**). "
                                    "Install `google-ads` if needed. Planner uses the same **Country** and "
                                    "**Target Domain / URL** (URL seed when provided)."
                                )
                    except ImportError:
                        pass

                if all_kws:
                    all_kws = _merge_keyword_rows(all_kws)
                    df_kw = pd.DataFrame(all_kws)
                    st.markdown(f"#### 💡 Keyword Ideas ({len(all_kws)})")
                    st.dataframe(df_kw, use_container_width=True, hide_index=True)
                    st.session_state["dr_all_keywords"] = all_kws
                    st.download_button("📥 Export Keywords CSV",
                                       df_kw.to_csv(index=False).encode(),
                                       f"kw_{dr_keyword}.csv", "text/csv")
                else:
                    st.info("No keyword ideas returned. Check API key and plan limits.")

    # ── Rank Tracker ─────────────────────────────────────────────────────────
    with tab_rank:
        st.markdown("### 📈 Rank Tracker")
        st.caption("Track current keyword positions, traffic and SERP features for your domain.")
        if not dr_url:
            st.info("Enter a domain URL above.")
        else:
            if st.button("🚀 Fetch Rankings", key="btn_rank"):
                with st.spinner(f"Fetching rankings for **{dr_url}**..."):
                    st.session_state["dr_rank_data"] = ah.rank_tracker_positions(
                        dr_url, dr_country, [dr_keyword] if dr_keyword else [], 100
                    )
            positions = st.session_state.get("dr_rank_data", [])
            if positions:
                rows = [
                    {"Keyword": p.get("keyword",""), "Position": p.get("position","—"),
                     "Traffic": fmt_num(p.get("traffic","—")), "Volume": fmt_num(p.get("volume","—")),
                     "KD": p.get("difficulty","—"), "CPC ($)": p.get("cpc","—")}
                    for p in positions if isinstance(p, dict)
                ]
                if rows:
                    df_r = pd.DataFrame(rows)
                    st.markdown(f"#### 🏆 Ranking Keywords ({len(rows)})")
                    st.dataframe(df_r, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Rankings CSV",
                                       df_r.to_csv(index=False).encode(),
                                       "rankings.csv", "text/csv")
            else:
                st.info("No ranking data. Click Fetch Rankings above.")

    # ── Content Explorer ─────────────────────────────────────────────────────
    with tab_content:
        st.markdown("### 📝 Content Explorer")
        st.caption("Find viral, high-performing content by topic — backlinks, traffic & social shares.")
        if not dr_keyword:
            st.info("Enter a keyword above.")
        else:
            if st.button("🚀 Explore Content", key="btn_ce"):
                with st.spinner(f"Exploring top content for **{dr_keyword}**..."):
                    st.session_state["dr_content_data"] = ah.content_explorer(dr_keyword, limit=20)
            articles = st.session_state.get("dr_content_data", [])
            if articles:
                for i, art in enumerate(articles, 1):
                    if not isinstance(art, dict):
                        continue
                    with st.expander(f"#{i} — {art.get('title', '')[:90]}"):
                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric("Traffic",     fmt_num(art.get("traffic", "—")))
                        c2.metric("Ref. Domains",fmt_num(art.get("referring_domains", "—")))
                        c3.metric("FB Shares",   fmt_num(art.get("facebook_shares", "—")))
                        c4.metric("Tweets",      fmt_num(art.get("twitter_shares", "—")))
                        c5.metric("Words",       fmt_num(art.get("words", "—")))
                        if art.get("domain"):
                            st.caption(f"🌐 {art['domain']}")
                        if art.get("url"):
                            st.markdown(f"🔗 [{art['url'][:80]}]({art['url']})")
            else:
                st.info("No content found. Click Explore Content.")

    # ── Site Explorer ────────────────────────────────────────────────────────
    with tab_site:
        st.markdown("### 🌐 Site Organic Explorer")
        st.caption("Analyze organic search traffic and ranked keyword distribution.")
        if not dr_url:
            st.info("Enter a domain URL above.")
        else:
            if st.button("🚀 Analyze Site", key="btn_site"):
                with st.spinner(f"Analyzing **{dr_url}** ({dr_country})..."):
                    st.session_state["dr_site_data"] = {
                        "overview":  ah.site_explorer_overview(dr_url, dr_country),
                        "org_kws":   ah.site_explorer_organic_keywords(dr_url, dr_country, 50),
                    }

            sd = st.session_state.get("dr_site_data", {})
            if sd:
                ov_s = sd.get("overview", {})
                if ov_s and "error" not in ov_s:
                    ms = ov_s
                    for nk in ("metrics", "data", "overview"):
                        if nk in ov_s:
                            ms = ov_s[nk]
                            break
                    st.markdown("#### 📊 Organic Domain Overview")
                    sc1, sc2 = st.columns(2)
                    _metric_card(sc1, "Organic Traffic", ms.get("org_traffic", "—"))
                    _metric_card(sc2, "Organic Keywords",  ms.get("org_keywords", "—"))
                elif ov_s.get("error"):
                    st.warning(f"Overview: {ov_s['error']}")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### 🔑 Organic Keywords Distribution")
                
                rows_ok = [
                    {"Keyword": k.get("keyword",""), "Position": k.get("position","—"),
                     "Traffic": fmt_num(k.get("traffic","—")), "Volume": fmt_num(k.get("volume","—")),
                     "KD": k.get("difficulty","—"), "CPC ($)": k.get("cpc","—")}
                    for k in sd.get("org_kws",[]) if isinstance(k, dict)
                ]
                if rows_ok:
                    st.dataframe(pd.DataFrame(rows_ok), use_container_width=True, hide_index=True)
                else:
                    st.info("No organic keyword data.")
            else:
                st.info("Click Analyze Site to load data.")


    # ── Deep Researched Keywords ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🧬 Deep Researched Keywords")
    st.caption("All keywords extracted via DataForSEO Keyword Explorer. Run Keyword Explorer above to populate.")

    all_kw_data = st.session_state.get("dr_all_keywords", [])
    if all_kw_data:
        df_deep = pd.DataFrame(all_kw_data)
        st.markdown(f"**{len(df_deep)} keywords** for `{dr_keyword}` in `{dr_country}`")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filter_src = st.multiselect(
                "Filter Source",
                options=df_deep["Source"].unique().tolist() if "Source" in df_deep.columns else [],
                default=df_deep["Source"].unique().tolist() if "Source" in df_deep.columns else [],
                key="dr_filter_src"
            )
        with fc2:
            search_f = st.text_input("Search Keywords", placeholder="filter by text...", key="dr_search")
        with fc3:
            st.selectbox("Sort By", ["Keyword","Volume","KD","CPC ($)"], key="dr_sort")

        df_show = df_deep.copy()
        if filter_src and "Source" in df_show.columns:
            df_show = df_show[df_show["Source"].isin(filter_src)]
        if search_f:
            df_show = df_show[df_show["Keyword"].str.contains(search_f, case=False, na=False)]

        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Export Deep Keywords CSV",
            df_show.to_csv(index=False).encode(),
            f"deep_kw_{dr_keyword}.csv", "text/csv", type="primary"
        )
    else:
        st.info("Run Keyword Explorer above to populate the deep keyword database.")


# ═════════════════════════════════════════════════════════════════════════════
# COMPETITOR ANALYSIS PAGE
# ═════════════════════════════════════════════════════════════════════════════

def page_competitor_analysis():
    import sys, os as _os
    import re
    from urllib.parse import urlparse
    sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    try:
        from app.services import dataforseo_service as ah
        from openai import OpenAI as _OAI
    except ImportError as e:
        st.error(f"Import error: {e}")
        return

    st.markdown("<h1>🔍 Competitor Analysis</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Analyze competitor URLs using DataForSEO, SERP & OpenAI to identify content gaps and strategic opportunities.</p>",
        unsafe_allow_html=True
    )

    with st.form("competitor_form"):
        fi1, fi2 = st.columns(2)
        with fi1:
            ca_kw  = st.text_input("🎯 Target Keyword", placeholder="e.g. best mechanical keyboards")
            ca_our = st.text_input("🏠 Your Domain (optional)", placeholder="yoursite.com")
        with fi2:
            ca_country = st.selectbox("🌍 Country", options=list(ah.COUNTRY_CODES.keys()), index=0)
            ca_comps   = st.text_area("🏁 Competitor URLs (one per line, max 5)", height=130,
                                       placeholder="https://competitor1.com\nhttps://competitor2.com")
        ca_submit = st.form_submit_button("🔍 Analyze Competitors", use_container_width=True, type="primary")

    if ca_submit:
        if not ca_kw:
            st.error("Enter a target keyword.")
            st.stop()

        stopwords = {
            "the", "and", "for", "with", "that", "from", "your", "best", "top", "vs",
            "you", "are", "how", "what", "why", "when", "where", "about", "this", "these",
            "those", "into", "over", "under", "near", "guide", "review", "reviews", "buy"
        }

        def _normalize_url(url):
            if not url:
                return ""
            u = url.strip()
            if not u:
                return ""
            if not u.startswith(("http://", "https://")):
                u = "https://" + u
            return u

        def _domain(url):
            try:
                parsed = urlparse(url)
                host = (parsed.hostname or "").lower()
                if host.startswith("www."):
                    host = host[4:]
                return host
            except Exception:
                return ""

        def _tokenize(text):
            toks = re.findall(r"[a-z0-9]+", (text or "").lower())
            return {t for t in toks if len(t) > 2 and t not in stopwords}

        def _intent_score(text, keyword):
            kw_t = _tokenize(keyword)
            tx_t = _tokenize(text)
            if not kw_t or not tx_t:
                return 0.0
            inter = len(kw_t.intersection(tx_t))
            return round(inter / max(1, len(kw_t)), 3)

        raw_urls = []
        for line in ca_comps.split("\n"):
            u = _normalize_url(line)
            if not u:
                continue
            raw_urls.append(u)

        # Step 1: SERP
        serp_results = []
        with st.spinner("Fetching SERP data..."):
            try:
                serp_key = _os.getenv("SERP_API_KEY", "")
                cc_s = ah._country_code(ca_country)
                sr = requests.get("https://serpapi.com/search", params={
                    "q": ca_kw, "api_key": serp_key, "gl": cc_s, "hl": "en", "num": 10
                }, timeout=20)
                if sr.status_code == 200:
                    serp_results = sr.json().get("organic_results", [])
            except Exception as e:
                st.warning(f"SERP fetch issue: {e}")

        # Step 1b: Relevance filtering of competitors
        serp_candidates = []
        for r in serp_results[:10]:
            link = _normalize_url(r.get("link", ""))
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            if not link:
                continue
            serp_candidates.append({
                "url": link,
                "domain": _domain(link),
                "score": _intent_score(f"{title} {snippet} {link}", ca_kw),
                "source": "serp"
            })

        input_candidates = []
        for u in raw_urls:
            input_candidates.append({
                "url": u,
                "domain": _domain(u),
                "score": _intent_score(u, ca_kw),
                "source": "input"
            })

        serp_domains = {c["domain"] for c in serp_candidates if c["domain"]}
        selected = []
        seen_urls = set()

        # Keep user-provided URLs first, but prioritize ones that appear in live SERP.
        for c in input_candidates:
            if not c["url"] or c["url"] in seen_urls:
                continue
            if c["domain"] in serp_domains or c["score"] >= 0.2:
                selected.append(c)
                seen_urls.add(c["url"])

        # Backfill with top SERP competitors so analysis stays intent-aligned.
        for c in sorted(serp_candidates, key=lambda x: x["score"], reverse=True):
            if len(selected) >= 5:
                break
            if not c["url"] or c["url"] in seen_urls:
                continue
            selected.append(c)
            seen_urls.add(c["url"])

        # Final fallback if SERP is thin: keep remaining user entries.
        for c in input_candidates:
            if len(selected) >= 5:
                break
            if c["url"] and c["url"] not in seen_urls:
                selected.append(c)
                seen_urls.add(c["url"])

        comp_urls = [s["url"] for s in selected[:5]]
        relevance_notes = [
            {"url": s["url"], "source": s["source"], "intent_score": s["score"]}
            for s in selected[:5]
        ]
        if raw_urls and len(raw_urls) > 5:
            st.warning("Only 5 most relevant competitor URLs were selected for analysis.")
        if raw_urls and comp_urls and set(comp_urls) != set(raw_urls[:len(comp_urls)]):
            st.info("Competitor list was refined using live SERP intent signals for more relevant results.")

        # Step 2: DataForSEO metrics
        comp_ahrefs = []
        if comp_urls:
            with st.spinner("Fetching DataForSEO competitor metrics..."):
                comp_ahrefs = ah.competitor_overview_batch(comp_urls, ca_country)

        # Step 3: Scrape headings
        def _scrape(url):
            try:
                from bs4 import BeautifulSoup as _BS
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                r = requests.get(url, timeout=10, headers=headers)
                soup = _BS(r.text, "html.parser")
                
                title = ""
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()
                    
                meta_t  = soup.find("meta", attrs={"name": "description"})
                meta    = meta_t.get("content", "") if meta_t else ""
                
                # Check for empty title or scrape blocks (like Amazon's 202 response or captcha bodies)
                h2_list = [t.get_text(strip=True) for t in soup.find_all("h2") if t.get_text(strip=True)]
                h3_list = [t.get_text(strip=True) for t in soup.find_all("h3") if t.get_text(strip=True)]
                
                if not title and not h2_list and not h3_list:
                    return {"url": url, "error": "This page blocked our automated scraper or returned no visible text headings (anti-bot protection)."}
                
                return {
                    "url": url, "title": title, "meta": meta,
                    "h1":  [t.get_text(strip=True) for t in soup.find_all("h1")],
                    "h2":  h2_list,
                    "h3":  h3_list,
                }
            except Exception as e:
                return {"url": url, "error": str(e)}

        comp_content = []
        if comp_urls:
            with st.spinner("Scraping competitor page structures..."):
                for curl in comp_urls:
                    comp_content.append(_scrape(curl))

        # Step 4: OpenAI gap analysis
        ai_gaps, ai_sug = [], []
        with st.spinner("Running AI content gap analysis..."):
            try:
                own_content = _scrape(_normalize_url(ca_our)) if ca_our else {}
                own_h2_h3 = (own_content.get("h2", []) + own_content.get("h3", [])) if own_content else []
                own_heading_set = {h.lower().strip() for h in own_h2_h3 if h}

                all_h = []
                filtered_h = []
                for cc_i in comp_content:
                    headings = cc_i.get("h2", []) + cc_i.get("h3", [])
                    all_h.extend(headings)
                    for h in headings:
                        score = _intent_score(h, ca_kw)
                        if score >= 0.2:
                            filtered_h.append(h)

                selected_headings = list(dict.fromkeys(filtered_h or all_h))[:100]
                h_str = "\n".join(f"- {h}" for h in selected_headings)
                serp_str = "\n".join(
                    f"- {r.get('title','')} — {r.get('snippet','')[:100]}"
                    for r in serp_results[:8]
                )
                own_str = "\n".join(f"- {h}" for h in own_h2_h3[:80]) if own_h2_h3 else "- Not provided"
                gap_prompt = (
                    f"You are an expert SEO content strategist.\n"
                    f"Target keyword: \"{ca_kw}\" | Country: {ca_country}\n\n"
                    f"SERP results:\n{serp_str}\n\n"
                    f"Competitor headings (H2/H3):\n{h_str}\n\n"
                    f"Our current page headings (H2/H3):\n{own_str}\n\n"
                    f"Only suggest gaps strongly tied to the target keyword and search intent.\n"
                    f"Ignore generic or off-topic sections.\n"
                    f"1. Identify 8 CONTENT GAPS: subtopics competitors cover that our content may miss.\n"
                    f"2. Provide 8 ACTIONABLE SUGGESTIONS to outrank competitors.\n\n"
                    f"Return ONLY valid JSON:\n"
                    f'{{\"content_gaps\":[...],\"suggestions\":[...]}}'
                )
                oai = _OAI(api_key=_os.getenv("OPENAI_API_KEY", ""))
                resp = oai.chat.completions.create(
                    model="gpt-4o-mini", max_tokens=1200,
                    messages=[
                        {"role": "system", "content": "Expert SEO strategist. Respond only with JSON."},
                        {"role": "user",   "content": gap_prompt},
                    ]
                )
                raw_gap = resp.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
                parsed  = json.loads(raw_gap)
                ai_gaps = parsed.get("content_gaps", [])
                ai_sug  = parsed.get("suggestions", [])
                if own_heading_set:
                    ai_gaps = [g for g in ai_gaps if g.lower().strip() not in own_heading_set]
            except Exception as e:
                st.warning(f"AI analysis: {e}")

        st.session_state["ca_res"] = {
            "serp": serp_results, "ahrefs": comp_ahrefs,
            "content": comp_content, "gaps": ai_gaps, "sug": ai_sug,
            "kw": ca_kw, "country": ca_country,
            "relevance_notes": relevance_notes,
        }

    res = st.session_state.get("ca_res")
    if not res:
        st.info("Fill in the form above and click Analyze Competitors.")
        return

    st.markdown(f"### 📊 Analysis Results — **{res['kw']}** ({res['country']})")
    st.markdown("---")
    t1, t2, t3, t4, t5 = st.tabs([
        "🔎 SERP Overview", "🔗 DataForSEO Metrics",
        "🕸️ Page Content", "🕳️ Content Gaps", "💡 AI Suggestions"
    ])

    with t1:
        serp = res.get("serp", [])
        if serp:
            st.dataframe(pd.DataFrame([{
                "Pos":     r.get("position","—"),
                "Title":   r.get("title","")[:70],
                "URL":     r.get("link",""),
                "Snippet": r.get("snippet","")[:100],
            } for r in serp]), use_container_width=True, hide_index=True)
        else:
            st.info("No SERP data. Check SerpAPI key.")

    with t2:
        rel_n = res.get("relevance_notes", [])
        if rel_n:
            st.caption("Selected competitors (intent filtered):")
            st.dataframe(pd.DataFrame(rel_n), use_container_width=True, hide_index=True)
        ah_d = res.get("ahrefs", [])
        if ah_d:
            st.dataframe(pd.DataFrame([{
                "URL":            d.get("url",""),
                "Domain Rating":  d.get("domain_rating","—"),
                "Org Traffic":    fmt_num(d.get("organic_traffic","—")),
                "Backlinks":      fmt_num(d.get("backlinks","—")),
                "Ref Domains":    fmt_num(d.get("referring_domains","—")),
                "Org Keywords":   fmt_num(d.get("organic_keywords","—")),
                "Error":          d.get("error",""),
            } for d in ah_d]), use_container_width=True, hide_index=True)
        else:
            st.info("No DataForSEO data. Enter competitor URLs and analyze.")

    with t3:
        for cc_i in res.get("content", []):
            url = cc_i.get("url", "")
            has_error = "error" in cc_i
            
            with st.expander(f"📄 {url[:70]}", expanded=True if has_error else False):
                if has_error:
                    st.error(f"⚠️ **Scraping Blocked**: `{cc_i['error']}`")
                    st.info(
                        "💡 **Why this happens**: Large e-commerce or media portals (such as Amazon) have strict bot-protection systems "
                        "that block automated scripts. You can still see their active search metrics under the **DataForSEO Metrics** tab! "
                        "Try testing this with standard informational blogs or articles for fully mapped heading content."
                    )
                else:
                    if cc_i.get("title"):
                        st.markdown(f"**Title:** {cc_i['title']}")
                    if cc_i.get("meta"):
                        st.caption(cc_i["meta"][:200])
                    for h in cc_i.get("h2", [])[:15]:
                        st.markdown(f"&nbsp;&nbsp;• {h}", unsafe_allow_html=True)
                    h3s = cc_i.get("h3", [])
                    if h3s:
                        st.markdown(
                            f"<div style='margin-top:8px;color:#94a3b8;font-size:0.78rem;"
                            f"font-weight:600;letter-spacing:.05em;'>H3 HEADINGS ({len(h3s)})</div>",
                            unsafe_allow_html=True,
                        )
                        for h in h3s[:20]:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;◦ {h}", unsafe_allow_html=True)

    with t4:
        st.markdown("#### 🕳️ Content Gaps Identified by AI")
        st.caption("Topics covered by competitors that your content should address.")
        gaps = res.get("gaps", [])
        if gaps:
            for i, g in enumerate(gaps, 1):
                st.markdown(
                    f"<div style='background:#1e293b;border:1px solid #f59e0b;border-radius:8px;"
                    f"padding:10px 14px;margin:6px 0;'>🕳️ <b>Gap {i}:</b> {g}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No gaps yet. Run analysis first.")

    with t5:
        st.markdown("#### 💡 AI-Powered Content Suggestions")
        sug = res.get("sug", [])
        if sug:
            for i, s in enumerate(sug, 1):
                st.markdown(
                    f"<div style='background:#0c4a6e;border:1px solid #0ea5e9;border-radius:8px;"
                    f"padding:10px 14px;margin:6px 0;'>💡 <b>Suggestion {i}:</b> {s}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No suggestions yet. Run analysis first.")


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h1>Studio UI</h1>", unsafe_allow_html=True)
    st.write("SEO Content Generator")
    st.markdown("---")
    nav_choice = st.radio(
        "Navigation",
        [
            "✨ Studio Pipeline",
            "📚 Content Library",
            "⚙️ Automations",
            "🔬 Deep Research",
            "🔍 Competitor Analysis",
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    try:
        health = requests.get("http://127.0.0.1:8800/health", timeout=2)
        if health.status_code == 200:
            st.success("🟢 API Core: Online")
        else:
            st.warning("🟡 API Core: Sync Issue")
    except Exception:
        st.error("🔴 API Core: Offline")
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.caption("Content Generation Tool v2.0")

# ── Routing ────────────────────────────────────────────────────────────────────
if nav_choice == "✨ Studio Pipeline":
    page_generate()
elif nav_choice == "📚 Content Library":
    page_view_existing()
elif nav_choice == "⚙️ Automations":
    page_automations()
elif nav_choice == "🔬 Deep Research":
    page_deep_research()
elif nav_choice == "🔍 Competitor Analysis":
    page_competitor_analysis()
