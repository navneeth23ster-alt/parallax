"""Group headlines that cover the same underlying event.

TF-IDF over title+summary, cosine similarity, greedy agglomeration.
A "story" is only interesting for framing analysis when 2+ distinct
outlets cover it, so single-outlet clusters are dropped by default.
"""

from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .fetch import Headline


@dataclass
class Story:
    headlines: list[Headline] = field(default_factory=list)

    @property
    def outlets(self) -> list[str]:
        return sorted({h.outlet for h in self.headlines})

    @property
    def label(self) -> str:
        # Shortest headline tends to be the most neutral label for the event
        return min((h.title for h in self.headlines), key=len)


def cluster_headlines(
    headlines: list[Headline],
    similarity_threshold: float = 0.15,
    min_outlets: int = 2,
) -> list[Story]:
    if len(headlines) < 2:
        return []

    texts = [f"{h.title}. {h.summary}" for h in headlines]
    vec = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 1), sublinear_tf=True
    )
    matrix = vec.fit_transform(texts)
    sim = cosine_similarity(matrix)

    # Single-linkage greedy agglomeration: a headline joins a cluster if it
    # is similar enough to ANY current member (headlines are short, so
    # seed-only comparison misses chains like AP<->CNN<->Guardian).
    assigned = [-1] * len(headlines)
    clusters: list[list[int]] = []
    for i in range(len(headlines)):
        if assigned[i] != -1:
            continue
        cluster = [i]
        assigned[i] = len(clusters)
        changed = True
        while changed:
            changed = False
            for j in range(len(headlines)):
                if assigned[j] != -1:
                    continue
                if max(sim[j, k] for k in cluster) >= similarity_threshold:
                    cluster.append(j)
                    assigned[j] = len(clusters)
                    changed = True
        clusters.append(cluster)

    stories = []
    for idx_list in clusters:
        story = Story(headlines=[headlines[i] for i in idx_list])
        if len(story.outlets) >= min_outlets:
            stories.append(story)

    # Most-covered events first — those are where framing contrast matters
    stories.sort(key=lambda s: len(s.outlets), reverse=True)
    return stories
