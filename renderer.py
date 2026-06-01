from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

from paper_model import Paper


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
DOCS_DIR = BASE_DIR / "docs"
TOP_READ_COUNT = 10
DEEP_READ_COUNT = 5


def _paper_url(paper: Paper) -> str:
    return f"https://arxiv.org/abs/{paper.arxiv_id}"


def _direction_counts(papers: list[Paper]) -> Counter[str]:
    return Counter(paper.direction for paper in papers)


def _trend_keywords(papers: list[Paper], limit: int = 5) -> list[str]:
    counts = Counter(keyword for paper in papers for keyword in paper.matched_keywords)
    return [keyword for keyword, _ in counts.most_common(limit)]


def _hot_direction(papers: list[Paper]) -> str:
    counts = _direction_counts(papers)
    return counts.most_common(1)[0][0] if counts else "暂无"


def _overview(papers: list[Paper]) -> str:
    if not papers:
        return "今天暂未检索到符合筛选条件的新论文。"
    hot_direction = _hot_direction(papers)
    keywords = "、".join(_trend_keywords(papers, 3)) or "暂无明显关键词"
    return (
        f"今天共筛选出 {len(papers)} 篇相关论文。"
        f"最热方向是“{hot_direction}”，趋势关键词包括 {keywords}。"
        f"建议优先阅读评分最高的 {min(DEEP_READ_COUNT, len(papers))} 篇论文。"
    )


def _terms() -> list[tuple[str, str]]:
    return [
        ("Audio-LLM", "面向音频理解或生成任务的多模态大语言模型。"),
        ("Semantic speech tokenizer", "把语音转换为紧凑离散表示，尽量保留语义信息。"),
        ("Neural codec", "使用神经网络压缩和重建音频的编码器与解码器。"),
        ("ASR", "Automatic Speech Recognition，自动语音识别。"),
    ]


def render_markdown(title: str, papers: list[Paper], target_date: date) -> str:
    trend_keywords = "、".join(_trend_keywords(papers)) or "暂无"
    lines = [
        f"# {title}",
        "",
        f"日期：{target_date.isoformat()}",
        "",
        "## 今日 3 分钟速览",
        "",
        _overview(papers),
        "",
        "## 统计",
        "",
        f"- 共分析论文数：{len(papers)}",
        f"- 最热方向：{_hot_direction(papers)}",
        f"- 推荐精读数量：{min(DEEP_READ_COUNT, len(papers))}",
        f"- 今日趋势关键词：{trend_keywords}",
        "",
        "## 今日必读 TOP 10",
        "",
    ]
    if papers:
        for index, paper in enumerate(papers[:TOP_READ_COUNT], start=1):
            lines.append(
                f"{index}. [{paper.title}]({_paper_url(paper)}) "
                f"- {paper.direction} / 评分 {paper.relevance_score}"
            )
    else:
        lines.append("暂无论文。")

    lines.extend(["", "## 论文精读卡片 TOP 5", ""])
    for index, paper in enumerate(papers[:DEEP_READ_COUNT], start=1):
        lines.extend(
            [
                f"### TOP{index} {paper.title}",
                "",
                f"- 作者：{', '.join(paper.authors)}",
                f"- 方向分类：{paper.direction}",
                f"- 相关性评分：{paper.relevance_score}",
                f"- 链接：{_paper_url(paper)}",
                "",
                paper.summary,
                "",
            ]
        )

    lines.extend(["## 原始论文列表", ""])
    for paper in papers:
        lines.append(f"- [{paper.title}]({_paper_url(paper)}) `{paper.arxiv_id}`")
    if not papers:
        lines.append("- 暂无论文。")
    return "\n".join(lines) + "\n"


def _render_stats(papers: list[Paper]) -> str:
    trend_keywords = "、".join(escape(keyword) for keyword in _trend_keywords(papers)) or "暂无"
    stats = [
        ("共分析论文数", str(len(papers))),
        ("最热方向", escape(_hot_direction(papers))),
        ("推荐精读数量", str(min(DEEP_READ_COUNT, len(papers)))),
        ("今日趋势关键词", trend_keywords),
    ]
    return "".join(
        f'<article class="stat-card"><span>{label}</span><strong>{value}</strong></article>'
        for label, value in stats
    )


def _render_distribution(papers: list[Paper]) -> str:
    counts = _direction_counts(papers)
    if not counts:
        return "<p>暂无方向分布数据。</p>"
    rows = "".join(
        f"<tr><td>{escape(direction)}</td><td>{count}</td></tr>"
        for direction, count in counts.most_common()
    )
    return f"<table><thead><tr><th>方向</th><th>论文数</th></tr></thead><tbody>{rows}</tbody></table>"


def _render_top_reads(papers: list[Paper]) -> str:
    if not papers:
        return "<p>暂无推荐论文。</p>"
    items = []
    for index, paper in enumerate(papers[:TOP_READ_COUNT], start=1):
        items.append(
            "<li>"
            f'<a href="{escape(_paper_url(paper), quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{escape(paper.title)}</a>"
            f'<span class="tag">{escape(paper.direction)}</span>'
            f'<span class="score">评分 {paper.relevance_score}</span>'
            "</li>"
        )
    return f'<ol class="top-list">{"".join(items)}</ol>'


def _render_deep_nav(papers: list[Paper]) -> str:
    if not papers:
        return "<p>暂无精读卡片。</p>"
    return "".join(
        f'<a href="#top{index}">[TOP{index}]</a>'
        for index, _ in enumerate(papers[:DEEP_READ_COUNT], start=1)
    )


def _render_deep_cards(papers: list[Paper]) -> str:
    if not papers:
        return "<p>暂无精读卡片。</p>"
    cards = []
    for index, paper in enumerate(papers[:DEEP_READ_COUNT], start=1):
        authors = escape(", ".join(paper.authors))
        cards.append(
            f'<article class="paper-card" id="top{index}">'
            f"<h3>TOP{index} {escape(paper.title)}</h3>"
            f'<p class="meta">作者：{authors}</p>'
            f'<p class="meta">发布时间：{escape(paper.published.isoformat())}</p>'
            f'<p><span class="tag">{escape(paper.direction)}</span> '
            f'<span class="score">相关性评分 {paper.relevance_score}</span></p>'
            f'<p class="summary">{escape(paper.summary)}</p>'
            f'<a href="{escape(_paper_url(paper), quote=True)}" target="_blank" rel="noopener noreferrer">'
            "查看 arXiv 原文</a>"
            "</article>"
        )
    return "".join(cards)


def _render_terms() -> str:
    return "".join(
        f"<article><h3>{escape(term)}</h3><p>{escape(description)}</p></article>"
        for term, description in _terms()
    )


def _render_raw_papers(papers: list[Paper]) -> str:
    if not papers:
        return "<p>暂无原始论文。</p>"
    items = []
    for paper in papers:
        items.append(
            "<li>"
            f'<a href="{escape(_paper_url(paper), quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{escape(paper.title)}</a>"
            f"<code>{escape(paper.arxiv_id)}</code>"
            "</li>"
        )
    return f'<ul class="raw-list">{"".join(items)}</ul>'


def render_html(title: str, papers: list[Paper], target_date: date) -> str:
    safe_title = escape(title)
    safe_date = escape(target_date.isoformat())
    safe_overview = escape(_overview(papers))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title} - {safe_date}</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <header class="hero">
    <div class="container">
      <p class="subtitle">Daily Research Digest</p>
      <h1>{safe_title}</h1>
      <p class="date">{safe_date}</p>
    </div>
  </header>
  <main class="container">
    <section class="stats">{_render_stats(papers)}</section>
    <section class="section-card">
      <h2>今日 3 分钟速览</h2>
      <p>{safe_overview}</p>
    </section>
    <section class="section-card">
      <h2>热门方向分布</h2>
      {_render_distribution(papers)}
    </section>
    <section class="section-card">
      <h2>今日必读 TOP 10</h2>
      {_render_top_reads(papers)}
    </section>
    <section class="section-card">
      <h2>精读卡片导航</h2>
      <nav class="deep-nav">{_render_deep_nav(papers)}</nav>
    </section>
    <section>
      <h2>论文精读卡片 TOP 5</h2>
      <div class="paper-list">{_render_deep_cards(papers)}</div>
    </section>
    <section class="section-card">
      <h2>术语小白卡</h2>
      <div class="term-grid">{_render_terms()}</div>
    </section>
    <section class="section-card">
      <h2>原始论文列表</h2>
      {_render_raw_papers(papers)}
    </section>
  </main>
</body>
</html>
"""


def write_digest_files(title: str, papers: list[Paper], target_date: date) -> tuple[Path, Path, Path]:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    markdown_path = OUTPUTS_DIR / f"{target_date.isoformat()}.md"
    html_path = DOCS_DIR / f"{target_date.isoformat()}.html"
    index_path = DOCS_DIR / "index.html"
    markdown_path.write_text(render_markdown(title, papers, target_date), encoding="utf-8")
    html = render_html(title, papers, target_date)
    html_path.write_text(html, encoding="utf-8")
    index_path.write_text(html, encoding="utf-8")
    return markdown_path, html_path, index_path
