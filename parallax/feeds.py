"""RSS feed registry — v1 region: Indian subcontinent.

Feeds carry an `owner` field: the ownership cluster as a checkable
public fact. This is NOT a political-lean rating — see DESIGN.md.
Corroboration tiers key on distinct owners: sister publications under
one owner correctly collapse to a single confirmation.

`note` is optional, dated, factual context. Display-only.

Original global feed list preserved in feeds_global.py.
"""

FEEDS = {
    # --- establishment broadsheets ---
    "The Hindu": {
        "url": "https://www.thehindu.com/feeder/default.rss",
        "owner": "Kasturi & Sons (The Hindu Group)",
        "country": "India",
    },
    "Business Line (The Hindu)": {
        "url": "https://www.thehindubusinessline.com/feeder/default.rss",
        "owner": "Kasturi & Sons (The Hindu Group)",
        "country": "India",
    },
    "Times of India": {
        "url": "https://timesofindia.indiatimes.com/rssfeedmostrecent.cms",
        "owner": "Bennett, Coleman & Co. (Times Group)",
        "country": "India",
    },
    "Hindustan Times": {
        "url": "https://www.hindustantimes.com/feeds/rss/latest/rssfeed.xml",
        "owner": "HT Media (Birla family)",
        "country": "India",
    },
    "LiveMint": {
        "url": "https://www.livemint.com/rss/news",
        "owner": "HT Media (Birla family)",
        "country": "India",
    },
    "Indian Express": {
        "url": "https://indianexpress.com/section/india/feed",
        "owner": "Indian Express Group (Goenka family)",
        "country": "India",
    },
    "NDTV": {
        "url": "https://feeds.feedburner.com/NDTV-LatestNews",
        "owner": "Adani Group (AMG Media Networks)",
        "note": "Founded independent 1988; acquired by Adani Group Dec 2022",
        "country": "India",
    },
    "News18": {
        "url": "https://www.news18.com/commonfeeds/v1/eng/rss/india.xml",
        "owner": "Network18 / Reliance Industries",
        "country": "India",
    },
    "Moneycontrol": {
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "owner": "Network18 / Reliance Industries",
        "country": "India",
    },
    "India Today": {
        "url": "https://www.indiatoday.in/rss/home",
        "owner": "Living Media (India Today Group)",
        "country": "India",
    },
    "ABP News": {
        "url": "https://www.abplive.com/home/feed",
        "owner": "ABP Group (Ananda Bazar Patrika)",
        "country": "India",
    },
    "Deccan Chronicle": {
        "url": "https://www.deccanchronicle.com/google_feeds.xml",
        "owner": "Deccan Chronicle Holdings",
        "country": "India",
    },

    # --- independent / investigative digital-native ---
    "Scroll.in": {
        "url": "https://feeds.feedburner.com/ScrollinArticles.rss",
        "owner": "Scroll Media (independent)",
        "country": "India",
    },
    "The Wire": {
        "url": "https://thewire.in/feed",
        "owner": "Foundation for Independent Journalism (nonprofit)",
        "country": "India",
    },
    "The News Minute": {
        "url": "https://www.thenewsminute.com/feed",
        "owner": "Spunklane Media (independent)",
        "country": "India",
    },

    # --- regional English ---
    "Onmanorama (Kerala)": {
        "url": "https://www.onmanorama.com/kerala.feeds.onmrss.xml",
        "owner": "Malayala Manorama Group (Kandathil family)",
        "country": "India",
    },
    "The Federal": {
        "url": "https://thefederal.com/feeds.xml",
        "owner": "The Federal (independent digital)",
        "country": "India",
    },
    "Telangana Today": {
        "url": "https://telanganatoday.com/feed",
        "owner": "Telangana Publications",
        "country": "India",
    },

    # --- international coverage of the subcontinent ---
    "BBC (India desk)": {
        "url": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
        "owner": "BBC (UK public corporation)",
        "country": "international",
    },
    "Al Jazeera (South Asia)": {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "owner": "Al Jazeera Media Network (Qatar state-funded)",
        "country": "international",
    },

    # --- neighboring subcontinent outlets ---
    "Dawn (Pakistan)": {
        "url": "https://www.dawn.com/feeds/home",
        "owner": "Pakistan Herald Publications (Haroon family)",
        "country": "Pakistan",
    },
    "The Daily Star (Bangladesh)": {
        "url": "https://www.thedailystar.net/rss.xml",
        "owner": "Mediaworld Ltd",
        "country": "Bangladesh",
    },
}
