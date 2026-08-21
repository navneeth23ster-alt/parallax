"""Original global (US/UK/international) feed registry, preserved.

Updated to the independence-cluster model (DESIGN.md): `owner` is the
checkable ownership fact used for corroboration tiering. `lean_allsides`
is retained as display-only context because audited public trackers
(AllSides, Ad Fontes) exist for these outlets — it is never used in
computation. Note the model's payoff here too: Fox News and the New York
Post are both Murdoch-family-controlled and now correctly share a
cluster.
"""

FEEDS = {
    "AP": {
        "url": "https://rsshub.app/apnews/topics/apf-topnews",
        "owner": "Associated Press (nonprofit cooperative)",
        "lean_allsides": "center",
        "country": "US",
    },
    "Reuters": {
        "url": "https://www.reutersagency.com/feed/?best-topics=top-news",
        "owner": "Thomson Reuters",
        "lean_allsides": "center",
        "country": "international",
    },
    "BBC": {
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "owner": "BBC (UK public corporation)",
        "lean_allsides": "center",
        "country": "UK",
    },
    "NPR": {
        "url": "https://feeds.npr.org/1001/rss.xml",
        "owner": "NPR (US public nonprofit)",
        "lean_allsides": "lean-left",
        "country": "US",
    },
    "New York Times": {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "owner": "The New York Times Company (Sulzberger family)",
        "lean_allsides": "lean-left",
        "country": "US",
    },
    "The Guardian": {
        "url": "https://www.theguardian.com/world/rss",
        "owner": "Scott Trust",
        "lean_allsides": "lean-left",
        "country": "UK",
    },
    "CNN": {
        "url": "http://rss.cnn.com/rss/cnn_topstories.rss",
        "owner": "Warner Bros. Discovery",
        "lean_allsides": "lean-left",
        "country": "US",
    },
    "Fox News": {
        "url": "https://moxie.foxnews.com/google-publisher/latest.xml",
        "owner": "Murdoch family (Fox Corp / News Corp)",
        "lean_allsides": "right",
        "country": "US",
    },
    "New York Post": {
        "url": "https://nypost.com/feed/",
        "owner": "Murdoch family (Fox Corp / News Corp)",
        "note": "Fox Corp and News Corp are formally separate companies "
                "under common Murdoch family control; treated as one "
                "cluster for independence purposes",
        "lean_allsides": "right",
        "country": "US",
    },
    "Wall Street Journal": {
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "owner": "Murdoch family (Fox Corp / News Corp)",
        "lean_allsides": "lean-right",
        "country": "US",
    },
    "Washington Post": {
        "url": "https://feeds.washingtonpost.com/rss/world",
        "owner": "Nash Holdings (Jeff Bezos)",
        "lean_allsides": "lean-left",
        "country": "US",
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "owner": "Al Jazeera Media Network (Qatar state-funded)",
        "lean_allsides": "international",
        "country": "international",
    },
}
