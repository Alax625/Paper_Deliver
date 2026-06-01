from paper_model import Paper


def score_paper(paper: Paper, keywords: list[str]) -> tuple[int, list[str]]:
    title = paper.title.casefold()
    summary = paper.summary.casefold()
    score = 0
    matched = []

    for keyword in keywords:
        normalized = keyword.strip().casefold()
        if not normalized:
            continue
        title_hits = title.count(normalized)
        summary_hits = summary.count(normalized)
        if title_hits or summary_hits:
            score += title_hits * 3 + summary_hits
            matched.append(keyword)

    return score, matched
