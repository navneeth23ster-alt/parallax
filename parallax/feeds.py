"""RSS feed registry — v1 region: Indian subcontinent.

Feeds carry a coarse "placement" tag for reader context, exactly as in
the original global list — BUT with one important difference, stated
plainly: no equivalent of AllSides/Ad Fontes exists for Indian media
with the same methodology, sample size, and public audit trail that
backed the earlier US placements. Indian media-bias assessment is more
contested and less standardized. So placements here are marked
"provisional" and rest on a thinner evidentiary base — outlet
ownership structure (a public fact) and broad reputational consensus
among Indian press-freedom researchers — not a scored, published
index. Treat them as orientation, not verdicts, and expect to revise
them as better public data becomes available.

The tool itself never scores outlets — it only compares their text —
so a wrong placement tag affects reader context, not any finding
Parallax reports.

Original global feed list preserved in feeds_global.py.
"""

FEEDS = {
    # --- wire / establishment broadsheets ---
    "The Hindu": {
        "url": "https://www.thehindu.com/feeder/default.rss",
        "placement": "center (provisional)",
        "country": "India",
    },
    "Times of India": {
        "url": "https://timesofindia.indiatimes.com/rssfeedmostrecent.cms",
        "placement": "center (provisional)",
        "country": "India",
    },
    "Hindustan Times": {
        "url": "https://www.hindustantimes.com/feeds/rss/latest/rssfeed.xml",
        "placement": "center (provisional)",
        "country": "India",
    },
    "Indian Express": {
        "url": "https://indianexpress.com/section/india/feed",
        "placement": "center (provisional)",
        "country": "India",
    },
    "NDTV": {
        "url": "https://feeds.feedburner.com/NDTV-LatestNews",
        # Founded independent, historically critical of government policy.
        # Acquired by Adani Group in Dec 2022 (Adani is closely tied to the
        # Modi government); RSF and multiple outlets have reported a
        # documented editorial shift since. Placement reflects ownership
        # as of this writing, not the outlet's historical reputation.
        "placement": "ownership-linked-to-govt (provisional)",
        "country": "India",
    },
    "News18": {
        "url": "https://www.news18.com/commonfeeds/v1/eng/rss/india.xml",
        # Part of Network18, majority-owned by Reliance Industries
        # (Mukesh Ambani), reported as close to the ruling government.
        "placement": "ownership-linked-to-govt (provisional)",
        "country": "India",
    },
    "India Today": {
        "url": "https://www.indiatoday.in/rss/home",
        "placement": "center (provisional)",
        "country": "India",
    },
    "ABP News": {
        "url": "https://www.abplive.com/home/feed",
        "placement": "center (provisional)",
        "country": "India",
    },
    "Deccan Chronicle": {
        "url": "https://www.deccanchronicle.com/google_feeds.xml",
        "placement": "center (provisional)",
        "country": "India",
    },
    "LiveMint": {
        "url": "https://www.livemint.com/rss/news",
        "placement": "center-business (provisional)",
        "country": "India",
    },
    "Moneycontrol": {
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "placement": "center-business (provisional)",
        "country": "India",
    },
    "Business Line (The Hindu)": {
        "url": "https://www.thehindubusinessline.com/feeder/default.rss",
        "placement": "center-business (provisional)",
        "country": "India",
    },

    # --- independent / investigative digital-native ---
    "Scroll.in": {
        "url": "https://feeds.feedburner.com/ScrollinArticles.rss",
        "placement": "independent (provisional)",
        "country": "India",
    },
    "The Wire": {
        "url": "https://thewire.in/feed",
        "placement": "independent-critical-of-govt (provisional)",
        "country": "India",
    },
    "The News Minute": {
        "url": "https://www.thenewsminute.com/feed",
        "placement": "independent (provisional)",
        "country": "India",
    },

    # --- regional English ---
    "Onmanorama (Kerala)": {
        "url": "https://www.onmanorama.com/kerala.feeds.onmrss.xml",
        "placement": "regional (provisional)",
        "country": "India",
    },
    "The Federal": {
        "url": "https://thefederal.com/feeds.xml",
        "placement": "regional-independent (provisional)",
        "country": "India",
    },
    "Telangana Today": {
        "url": "https://telanganatoday.com/feed",
        "placement": "regional (provisional)",
        "country": "India",
    },

    # --- international coverage of the subcontinent (established trackers apply) ---
    "BBC (India desk)": {
        "url": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
        "placement": "center",
        "country": "international",
    },
    "Al Jazeera (South Asia)": {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "placement": "international",
        "country": "international",
    },

    # --- neighboring subcontinent outlets ---
    "Dawn (Pakistan)": {
        "url": "https://www.dawn.com/feeds/home",
        "placement": "center (provisional)",
        "country": "Pakistan",
    },
    "The Daily Star (Bangladesh)": {
        "url": "https://www.thedailystar.net/rss.xml",
        "placement": "center (provisional)",
        "country": "Bangladesh",
    },
}
