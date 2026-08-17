"""RSS feed registry for major outlets.

Outlets are tagged with a coarse, publicly documented placement drawn from
media-bias trackers (AllSides / Ad Fontes). The tag is metadata for the
reader's context — the tool itself never scores outlets, only compares text.
"""

FEEDS = {
    "AP": {
        "url": "https://rsshub.app/apnews/topics/apf-topnews",
        "fallback": "https://apnews.com/hub/ap-top-news",
        "placement": "center",
    },
    "Reuters": {
        "url": "https://www.reutersagency.com/feed/?best-topics=top-news",
        "placement": "center",
    },
    "BBC": {
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "placement": "center",
    },
    "NPR": {
        "url": "https://feeds.npr.org/1001/rss.xml",
        "placement": "lean-left",
    },
    "New York Times": {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "placement": "lean-left",
    },
    "The Guardian": {
        "url": "https://www.theguardian.com/world/rss",
        "placement": "lean-left",
    },
    "CNN": {
        "url": "http://rss.cnn.com/rss/cnn_topstories.rss",
        "placement": "lean-left",
    },
    "Fox News": {
        "url": "https://moxie.foxnews.com/google-publisher/latest.xml",
        "placement": "right",
    },
    "Wall Street Journal": {
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "placement": "lean-right",
    },
    "Washington Post": {
        "url": "https://feeds.washingtonpost.com/rss/world",
        "placement": "lean-left",
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "placement": "international",
    },
    "New York Post": {
        "url": "https://nypost.com/feed/",
        "placement": "right",
    },
}
