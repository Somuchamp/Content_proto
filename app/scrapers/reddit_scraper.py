import praw
import re
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# ── Topic → Subreddit mapping ─────────────────────────────────────────────────
TOPIC_SUBREDDITS = [
    # Skincare / Beauty
    (
        {"moisturizer", "skincare", "skin", "serum", "retinol", "sunscreen",
         "spf", "cleanser", "toner", "beauty", "makeup", "cosmetic", "lotion",
         "cream", "acne", "eczema", "dermatolog", "hyaluronic", "collagen",
         "cerave", "neutrogena", "cetaphil", "olay", "clinique", "laneige",
         "ordinary", "niacinamide", "vitamin", "moisturis"},
        "SkincareAddiction+AsianBeauty+DIYBeauty+beauty+MakeupAddiction"
    ),
    # Fashion / Clothing / Footwear brands + generic
    (
        {"clothing", "fashion", "dress", "shirt", "shoes", "sneaker", "jacket",
         "jeans", "outfit", "apparel", "wear", "style", "wardrobe", "bag",
         "handbag", "watch", "jewel", "accessory", "boot", "trouser", "pants",
         "hoodie", "sweater", "coat", "suit", "blazer", "skirt", "legging",
         # Major fashion/footwear brands
         "nike", "adidas", "puma", "reebok", "newbalance", "asics", "vans",
         "converse", "jordan", "yeezy", "gucci", "prada", "zara", "hm",
         "uniqlo", "levi", "wrangler", "timberland", "clarks", "skechers",
         "underarmour", "lululemon", "gymshark", "northface", "columbia",
         "patagonia", "supreme", "stussy", "carhartt", "dickies", "gap",
         "oldnavy", "forever", "balenciaga", "versace", "armani", "polo",
         "ralphlauren", "tommy", "calvinklein", "lacoste", "fila", "champion"},
        "Sneakers+streetwear+femalefashionadvice+malefashionadvice+fashion+RunningShoeGeeks"
    ),
    # Health / Supplements / Nutrition
    (
        {"supplement", "vitamin", "protein", "probiotic", "health", "nutrition",
         "wellness", "fitness", "weight", "diet", "keto", "omega", "mineral",
         "collagen", "magnesium", "zinc", "iron", "creatine", "whey",
         "multivitamin", "ashwagandha", "melatonin", "biotin"},
        "Supplements+nutrition+Health+HealthyFood+loseit+Fitness"
    ),
    # Solar / Renewable Energy
    (
        {"solar", "panel", "photovoltaic", "renewable", "energy", "battery",
         "inverter", "generator", "wind", "power", "electricity", "watt",
         "kilowatt", "grid", "offgrid", "portable", "charger"},
        "solar+renewable_energy+energy+SolarDIY+homeautomation+vandwellers"
    ),
    # Electronics / Tech / Gadgets
    (
        {"phone", "laptop", "tablet", "headphone", "earphone", "speaker",
         "camera", "monitor", "keyboard", "mouse", "gaming", "gpu", "cpu",
         "processor", "router", "gadget", "electronic", "tech", "smartwatch",
         "drone", "printer", "scanner", "iphone", "samsung", "apple", "sony",
         "bose", "jabra", "anker", "logitech", "razer", "corsair", "asus",
         "dell", "lenovo", "microsoft", "surface", "pixel", "android"},
        "gadgets+electronics+hardware+techsupport+Smartphones+headphones"
    ),
    # Home / Furniture / Appliances
    (
        {"furniture", "sofa", "couch", "mattress", "pillow", "bedding",
         "appliance", "refrigerator", "washing", "vacuum", "dishwasher",
         "kitchen", "cookware", "home", "decor", "interior", "lamp",
         "ikea", "dyson", "roomba", "instant", "cuisinart", "kitchenaid"},
        "HomeImprovement+InteriorDesign+malelivingspace+Appliances+DIY"
    ),
    # Automotive
    (
        {"car", "vehicle", "automotive", "tire", "engine", "motor", "bike",
         "motorcycle", "oil", "brake", "battery", "dashcam", "seat",
         "toyota", "honda", "ford", "bmw", "mercedes", "tesla", "audi",
         "volkswagen", "nissan", "hyundai", "kia", "chevrolet", "jeep"},
        "cars+Cartalk+Justrolledintotheshop+motorcycles+autodetailing"
    ),
    # Food / Cooking
    (
        {"food", "recipe", "cooking", "baking", "ingredient", "meal", "diet",
         "snack", "drink", "beverage", "coffee", "tea", "wine", "restaurant",
         "nespresso", "keurig", "airfryer", "instant"},
        "food+Cooking+recipes+MealPrepSunday+EatCheapAndHealthy+Coffee"
    ),
    # Baby / Kids / Parenting
    (
        {"baby", "infant", "toddler", "kids", "child", "parenting", "stroller",
         "diaper", "formula", "toy", "school", "education", "pampers", "huggies"},
        "Parenting+beyondthebump+BabyBumps+daddit+Mommit"
    ),
    # Pets
    (
        {"pet", "dog", "cat", "puppy", "kitten", "fish", "bird", "hamster",
         "reptile", "veterinary", "vet", "animal", "pedigree", "purina",
         "royalcanin", "whiskas"},
        "dogs+cats+Pets+AskVet+puppy101"
    ),
]

# Fallback: only used when no topic matches — more focused than before
FALLBACK_SUBREDDITS = "Recommendations+ProductReviews+whichcar+SuggestALaptop+findaReddit"

# Generic words that appear in almost every query — useless for topic matching
_TOPIC_STOPWORDS = {
    "best", "top", "good", "great", "review", "reviews", "buy", "cheap",
    "affordable", "price", "cost", "deal", "discount", "sale", "free",
    "new", "latest", "popular", "recommended", "guide", "how", "what",
    "why", "when", "where", "which", "for", "and", "the", "with", "from",
    "that", "this", "are", "use", "used", "get", "pro", "plus", "max",
    "ultra", "super", "mega", "mini", "lite", "edition", "version",
    "product", "products", "item", "brand", "category", "keyword",
}


def _resolve_subreddits(query: str) -> str:
    """
    Match query keywords against TOPIC_SUBREDDITS.
    Returns the best matching subreddit string, or FALLBACK_SUBREDDITS.
    """
    query_words = set(re.findall(r"[a-z]{3,}", query.lower())) - _TOPIC_STOPWORDS

    best_match = None
    best_score = 0

    for topic_keywords, subreddits in TOPIC_SUBREDDITS:
        score = 0
        for qw in query_words:
            for tk in topic_keywords:
                if qw in tk or tk in qw:
                    score += 1
                    break
        if score > best_score:
            best_score = score
            best_match = subreddits

    if best_match and best_score >= 1:
        logger.info(f"Reddit subreddit match: score={best_score} → {best_match}")
        return best_match

    logger.info(f"Reddit: no topic match for '{query}' — using fallback subreddits")
    return FALLBACK_SUBREDDITS


def _filter_by_title_relevance(results: list[dict], query: str) -> list[dict]:
    """
    Post-fetch safety net: remove any post whose title does NOT contain
    at least one meaningful query word.

    This catches cases where subreddit routing was correct but Reddit still
    surfaced off-topic posts (e.g. searching 'nike' in r/Sneakers but getting
    a generic 'best boots under $300' post that never mentions nike).

    Meaningful words = query words minus generic stopwords.
    If no meaningful words exist (very short/generic query), returns all results.
    """
    meaningful = set(re.findall(r"[a-z]{3,}", query.lower())) - _TOPIC_STOPWORDS

    if not meaningful:
        return results  # Can't filter — return everything

    filtered = [
        r for r in results
        if any(w in r["title"].lower() for w in meaningful)
    ]

    dropped = len(results) - len(filtered)
    if dropped > 0:
        logger.info(
            f"Reddit title filter: dropped {dropped}/{len(results)} irrelevant posts "
            f"(meaningful_words={meaningful})"
        )

    return filtered


class RedditScraper:
    def __init__(self):
        s = get_settings()
        if s.REDDIT_CLIENT_ID and s.REDDIT_CLIENT_SECRET:
            self.reddit = praw.Reddit(
                client_id=s.REDDIT_CLIENT_ID,
                client_secret=s.REDDIT_CLIENT_SECRET,
                user_agent=s.REDDIT_USER_AGENT,
            )
        else:
            self.reddit = None

    def fetch(self, query: str, country: str, max_posts: int = 10) -> list[dict]:
        """
        Search Reddit for posts related to query in topic-specific subreddits.

        FIXES vs old version:
          1. Routes to topic-specific subreddits instead of r/all.
          2. Brand names (nike, adidas, sony etc.) added to topic keyword sets
             so brand queries correctly route to relevant subreddits.
          3. Removed country + 'trends' from search query — noise words.
          4. sort='top' instead of sort='relevance' — more trustworthy.
          5. Post-fetch title relevance filter (_filter_by_title_relevance)
             drops any post whose title doesn't contain a meaningful query word.
             This is the safety net even when subreddit routing is imperfect.
          6. Fetches more posts (max_posts=10, limit=15) to compensate for
             posts that get filtered out by the title relevance check.
        """
        if not self.reddit:
            logger.warning("Reddit credentials not set. Skipping.")
            return []

        clean_query = query.strip()
        subreddit_str = _resolve_subreddits(clean_query)

        try:
            raw_results = []
            # Fetch slightly more than needed to account for title filtering
            fetch_limit = max(max_posts + 5, 15)
            for post in self.reddit.subreddit(subreddit_str).search(
                clean_query,
                sort="top",
                time_filter="year",
                limit=fetch_limit,
            ):
                raw_results.append({
                    "source": "reddit",
                    "title": post.title,
                    "description": post.selftext[:500] if post.selftext else "",
                    "url": f"https://www.reddit.com{post.permalink}",
                })

            # Apply post-fetch title relevance filter
            filtered = _filter_by_title_relevance(raw_results, clean_query)

            logger.info(
                f"Reddit: {len(raw_results)} fetched → {len(filtered)} after filter "
                f"| subreddits='{subreddit_str}' | query='{clean_query}'"
            )
            return filtered[:max_posts]

        except Exception as e:
            logger.error(f"Reddit scrape failed for subreddits='{subreddit_str}': {e}")
            # Last resort: r/all with title filter
            try:
                raw_results = []
                for post in self.reddit.subreddit("all").search(
                    clean_query, sort="top", time_filter="year", limit=15
                ):
                    raw_results.append({
                        "source": "reddit",
                        "title": post.title,
                        "description": post.selftext[:500] if post.selftext else "",
                        "url": f"https://www.reddit.com{post.permalink}",
                    })
                filtered = _filter_by_title_relevance(raw_results, clean_query)
                logger.info(f"Reddit fallback r/all: {len(filtered)} posts after filter")
                return filtered[:max_posts]
            except Exception as e2:
                logger.error(f"Reddit fallback also failed: {e2}")
                return []