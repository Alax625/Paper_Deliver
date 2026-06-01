from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

from paper_model import Paper
from summarizer import DigestAnalysis, analyze_digest


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


def _terms() -> list[tuple[str, str, str]]:
    return [
        ("AI", "Audio-LLM", "面向音频理解或生成任务的多模态大语言模型。"),
        ("TK", "Semantic speech tokenizer", "把语音转换为紧凑离散表示，尽量保留语义信息。"),
        ("NC", "Neural codec", "使用神经网络压缩和重建音频的编码器与解码器。"),
        ("ASR", "ASR", "Automatic Speech Recognition，自动语音识别。"),
    ]


def _short_text(value: str, limit: int = 150) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _why_read(paper: Paper) -> str:
    keyword = paper.matched_keywords[0] if paper.matched_keywords else paper.direction
    return f"聚焦 {keyword}，在 {paper.direction} 方向具有较高相关度。"


def render_markdown(
    title: str,
    papers: list[Paper],
    target_date: date,
    analysis: DigestAnalysis | None = None,
    deep_read_top_k: int = DEEP_READ_COUNT,
) -> str:
    analysis = analysis or analyze_digest(papers, deep_read_top_k)
    trend_keywords = "、".join(_trend_keywords(papers)) or "暂无"
    lines = [
        f"# {title}",
        "",
        f"日期：{target_date.isoformat()}",
        f"分析来源：{analysis.source}",
        "",
        "## 今日 3 分钟速览",
        "",
        f"- 今日主线：{analysis.overview['main_line']}",
        f"- 今日值得关注：{analysis.overview['worth_attention']}",
        f"- 今日方法趋势：{analysis.overview['method_trend']}",
        f"- 今日避坑提醒：{analysis.overview['risk_note']}",
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
    for index, paper in enumerate(papers[:deep_read_top_k], start=1):
        insights = analysis.paper_insights[paper.arxiv_id]
        lines.extend(
            [
                f"### TOP{index} {paper.title}",
                "",
                f"- 作者：{', '.join(paper.authors)}",
                f"- 方向分类：{paper.direction}",
                f"- 相关性评分：{paper.relevance_score}",
                f"- 链接：{_paper_url(paper)}",
                "",
                f"- 一句话总结：{insights['one_sentence_summary']}",
                f"- 解决了什么问题：{insights['problem']}",
                f"- 核心方法：{insights['core_method']}",
                f"- 主要创新点：{insights['innovations']}",
                f"- 实验结论：{insights['experiment_conclusion']}",
                f"- 可能局限：{insights['limitations']}",
                f"- 适合谁读：{insights['audience']}",
                f"- 和已有工作的关系：{insights['related_work']}",
                f"- 对研究的启发：{insights['research_inspiration']}",
                f"- 是否值得精读：{insights['worth_deep_reading']}",
                "",
            ]
        )

    lines.extend(["## 原始论文列表", ""])
    for paper in papers:
        lines.append(f"- [{paper.title}]({_paper_url(paper)}) `{paper.arxiv_id}`")
    if not papers:
        lines.append("- 暂无论文。")
    return "\n".join(lines) + "\n"


def _render_stats(papers: list[Paper], deep_read_top_k: int) -> str:
    trend_keywords = "、".join(escape(keyword) for keyword in _trend_keywords(papers)) or "暂无"
    stats = [
        ("&#128202;", "共分析", str(len(papers)), "篇近期相关论文"),
        ("&#128293;", "最热门方向", escape(_hot_direction(papers)), "今日研究主线"),
        ("&#128214;", "推荐精读", str(min(deep_read_top_k, len(papers))), "篇优先阅读"),
        ("&#128273;", "今日关键词", trend_keywords, "高频趋势线索"),
    ]
    return "".join(
        f'<article class="stat-card"><span class="stat-icon">{icon}</span>'
        f'<div><span class="stat-label">{label}</span><strong>{value}</strong><small>{note}</small></div></article>'
        for icon, label, value, note in stats
    )


def _render_distribution(papers: list[Paper]) -> str:
    counts = _direction_counts(papers)
    if not counts:
        return "<p>暂无方向分布数据。</p>"
    maximum = max(counts.values())
    bars = "".join(
        f'<div class="direction-row"><div class="direction-meta"><strong>{escape(direction)}</strong>'
        f"<span>{count} 篇</span></div><div class=\"progress-track\">"
        f'<span class="progress-bar" style="width: {count / maximum * 100:.0f}%"></span></div></div>'
        for direction, count in counts.most_common()
    )
    return f'<div class="direction-bars">{bars}</div>'


def _render_top_reads(papers: list[Paper]) -> str:
    if not papers:
        return "<p>暂无推荐论文。</p>"
    rows = []
    for index, paper in enumerate(papers[:TOP_READ_COUNT], start=1):
        rank_class = f" rank-{index}" if index <= 3 else ""
        rows.append(
            "<tr>"
            f'<td><span class="rank-badge{rank_class}">{index}</span></td>'
            "<td>"
            f'<a href="{escape(_paper_url(paper), quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{escape(paper.title)}</a>"
            "</td>"
            f'<td><span class="score">{paper.relevance_score}</span></td>'
            f'<td><span class="tag">{escape(paper.direction)}</span></td>'
            f"<td>{escape(_why_read(paper))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-scroll"><table class="top-table"><thead><tr>'
        "<th>排名</th><th>论文标题</th><th>评分</th><th>方向</th><th>为什么值得看</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def _render_deep_nav(papers: list[Paper], deep_read_top_k: int) -> str:
    if not papers:
        return "<p>暂无精读卡片。</p>"
    return "".join(
        f'<a href="#top{index}">[TOP{index}]</a>'
        for index, _ in enumerate(papers[:deep_read_top_k], start=1)
    )


def _render_deep_cards(papers: list[Paper], analysis: DigestAnalysis, deep_read_top_k: int) -> str:
    if not papers:
        return "<p>暂无精读卡片。</p>"
    cards = []
    for index, paper in enumerate(papers[:deep_read_top_k], start=1):
        authors = escape(", ".join(paper.authors))
        insights = {
            key: escape(value) for key, value in analysis.paper_insights[paper.arxiv_id].items()
        }
        keywords = "".join(
            f'<span class="keyword-tag">{escape(keyword)}</span>' for keyword in paper.matched_keywords[:6]
        )
        cards.append(
            f'<article class="paper-card" id="top{index}">'
            '<div class="paper-card-head">'
            f'<span class="top-badge">TOP {index}</span><div><h3>{escape(paper.title)}</h3>'
            f'<p class="meta">作者：{authors}</p></div></div>'
            '<div class="paper-card-toolbar">'
            f'<span class="tag">{escape(paper.direction)}</span><span class="score">评分 {paper.relevance_score}</span>'
            f"{keywords}"
            f'<a class="paper-link" href="{escape(_paper_url(paper), quote=True)}" target="_blank" rel="noopener noreferrer">'
            "查看 arXiv &#8599;</a></div>"
            '<div class="paper-detail-grid"><div>'
            f'<div class="insight"><h4>一句话总结</h4><p>{insights["one_sentence_summary"]}</p></div>'
            f'<div class="insight"><h4>解决了什么问题</h4><p>{insights["problem"]}</p></div>'
            f'<div class="insight"><h4>核心方法</h4><p>{insights["core_method"]}</p></div>'
            f'<div class="insight"><h4>主要创新点</h4><p>{insights["innovations"]}</p></div>'
            f'<div class="insight"><h4>实验结论</h4><p>{insights["experiment_conclusion"]}</p></div>'
            '</div><div class="detail-side">'
            f'<div class="insight"><h4>可能局限</h4><p>{insights["limitations"]}</p></div>'
            f'<div class="insight"><h4>适合谁读</h4><p>{insights["audience"]}</p></div>'
            f'<div class="insight"><h4>和已有工作的关系</h4><p>{insights["related_work"]}</p></div>'
            f'<div class="insight"><h4>对研究的启发</h4><p>{insights["research_inspiration"]}</p></div>'
            f'<div class="insight"><h4>是否值得精读</h4><p>{insights["worth_deep_reading"]}</p></div>'
            "</div></div>"
            "</article>"
        )
    return "".join(cards)


def _render_terms() -> str:
    return "".join(
        f'<article><span class="term-icon">{escape(icon)}</span><h3>{escape(term)}</h3>'
        f"<p>{escape(description)}</p></article>"
        for icon, term, description in _terms()
    )


def _render_raw_papers(papers: list[Paper]) -> str:
    if not papers:
        return "<p>暂无原始论文。</p>"
    items = []
    for paper in papers:
        items.append(
            '<article class="raw-paper"><div>'
            f'<a href="{escape(_paper_url(paper), quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{escape(paper.title)}</a>"
            f"<code>{escape(paper.arxiv_id)}</code>"
            f'<span class="tag">{escape(paper.direction)}</span></div>'
            f"<details><summary>展开摘要</summary><p>{escape(paper.summary)}</p></details></article>"
        )
    return f'<div class="raw-list">{"".join(items)}</div>'


def _render_overview_modules(papers: list[Paper], analysis: DigestAnalysis) -> str:
    if not papers:
        return "<p>今天暂未检索到符合筛选条件的新论文。</p>"
    modules = [
        ("blue", "&#9679;", "今日主线", analysis.overview["main_line"]),
        ("green", "&#9679;", "今日值得关注", analysis.overview["worth_attention"]),
        ("purple", "&#9679;", "今日方法趋势", analysis.overview["method_trend"]),
        ("orange", "&#9679;", "今日避坑提醒", analysis.overview["risk_note"]),
    ]
    return "".join(
        f'<article class="overview-item {color}"><span>{icon}</span><div><h3>{heading}</h3><p>{escape(body)}</p></div></article>'
        for color, icon, heading, body in modules
    )


def render_html(
    title: str,
    papers: list[Paper],
    target_date: date,
    analysis: DigestAnalysis | None = None,
    deep_read_top_k: int = DEEP_READ_COUNT,
) -> str:
    analysis = analysis or analyze_digest(papers, deep_read_top_k)
    safe_title = escape(title)
    safe_date = escape(target_date.isoformat())
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
    <div class="container hero-inner">
      <div>
        <p class="subtitle">Daily Research Digest</p>
        <h1>{safe_title}</h1>
        <p class="hero-note">聚焦语音、音乐与音频智能的每日研究动态</p>
      </div>
      <div class="hero-meta">
        <strong>{safe_date}</strong>
        <span>每日更新 · 学术前沿 · 一图速览</span>
      </div>
    </div>
  </header>
  <main class="container">
    <section class="stats">{_render_stats(papers, deep_read_top_k)}</section>
    <section class="section-card overview-section">
      <div class="section-heading"><span>01</span><div><h2>今日 3 分钟速览</h2><p>快速把握今日研究信号</p></div></div>
      <div class="overview-grid">{_render_overview_modules(papers, analysis)}</div>
    </section>
    <section class="section-card">
      <div class="section-heading"><span>02</span><div><h2>热门方向分布</h2><p>按论文方向统计今日关注度</p></div></div>
      {_render_distribution(papers)}
    </section>
    <section class="section-card">
      <div class="section-heading"><span>03</span><div><h2>今日必读 TOP 10</h2><p>优先浏览评分较高的研究</p></div></div>
      {_render_top_reads(papers)}
    </section>
    <section class="section-card compact-section">
      <div class="section-heading"><span>04</span><div><h2>精读卡片导航</h2><p>点击编号快速定位</p></div></div>
      <nav class="deep-nav">{_render_deep_nav(papers, deep_read_top_k)}</nav>
    </section>
    <section class="deep-section">
      <div class="section-heading"><span>05</span><div><h2>论文精读卡片 TOP 5</h2><p>基于摘要的中文研究分析 · {escape(analysis.source)}</p></div></div>
      <div class="paper-list">{_render_deep_cards(papers, analysis, deep_read_top_k)}</div>
    </section>
    <section class="section-card">
      <div class="section-heading"><span>06</span><div><h2>术语小白卡</h2><p>快速补齐今日阅读背景</p></div></div>
      <div class="term-grid">{_render_terms()}</div>
    </section>
    <section class="section-card">
      <div class="section-heading"><span>07</span><div><h2>原始论文列表</h2><p>点击标题访问 arXiv，展开查看摘要</p></div></div>
      {_render_raw_papers(papers)}
    </section>
  </main>
  <footer>Paper_Deliver · Generated from arXiv API</footer>
</body>
</html>
"""


def write_digest_files(
    title: str,
    papers: list[Paper],
    target_date: date,
    deep_read_top_k: int = DEEP_READ_COUNT,
) -> tuple[Path, Path, Path, DigestAnalysis]:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    markdown_path = OUTPUTS_DIR / f"{target_date.isoformat()}.md"
    html_path = DOCS_DIR / f"{target_date.isoformat()}.html"
    index_path = DOCS_DIR / "index.html"
    analysis = analyze_digest(papers, deep_read_top_k)
    markdown_path.write_text(
        render_markdown(title, papers, target_date, analysis, deep_read_top_k), encoding="utf-8"
    )
    html = render_html(title, papers, target_date, analysis, deep_read_top_k)
    html_path.write_text(html, encoding="utf-8")
    index_path.write_text(html, encoding="utf-8")
    return markdown_path, html_path, index_path, analysis
