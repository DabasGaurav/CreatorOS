"""engagement_rate is undefined by the spec — this is an explicit assumption, not a
given formula. Shared between the embedding job (Qdrant payload) and Creator DNA
aggregation so both use the same definition."""


def compute_engagement_rate(
    *,
    likes: int | None,
    comments: int | None,
    shares: int | None,
    saves: int | None,
    reach: int | None,
) -> float | None:
    if not reach:
        return None
    numerator = sum(v or 0 for v in (likes, comments, shares, saves))
    return numerator / reach
