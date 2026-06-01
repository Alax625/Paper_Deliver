import json
import logging
import os
from collections import Counter
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

from paper_model import Paper


LOGGER = logging.getLogger(__name__)

OVERVIEW_FIELDS = ["main_line", "worth_attention", "method_trend", "risk_note"]
PAPER_FIELDS = [
    "one_sentence_summary",
    "problem",
    "core_method",
    "innovations",
    "experiment_conclusion",
    "limitations",
    "audience",
    "related_work",
    "research_inspiration",
    "worth_deep_reading",
]


@dataclass
class DigestAnalysis:
    overview: dict[str, str]
    paper_insights: dict[str, dict[str, str]]
    source: str = "规则模板"


def _short_text(value: str, limit: int = 180) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _keywords(paper: Paper) -> str:
    return "、".join(paper.matched_keywords[:4]) or paper.direction


def _rule_paper_insights(paper: Paper) -> dict[str, str]:
    keywords = _keywords(paper)
    return {
        "one_sentence_summary": _short_text(paper.summary),
        "problem": f"论文关注 {paper.direction} 场景中的问题，摘要线索集中在 {keywords}。",
        "core_method": f"论文围绕 {keywords} 展开方法设计。更具体的模型结构需要阅读全文确认。",
        "innovations": f"从摘要可见，该工作尝试在 {paper.direction} 方向整合或改进现有能力。",
        "experiment_conclusion": "摘要中未明确说明。",
        "limitations": "摘要提供的信息有限，实验设置、数据规模和适用边界需要阅读全文确认。",
        "audience": f"适合关注 {paper.direction}、音频建模和近期研究趋势的读者。",
        "related_work": "摘要中未明确说明。",
        "research_inspiration": f"可关注 {keywords} 是否能迁移到自己的任务和数据设置中。",
        "worth_deep_reading": "建议先读摘要和方法图，再根据实验设置决定是否精读全文。",
    }


def _trend_keywords(papers: list[Paper], limit: int = 4) -> list[str]:
    counts = Counter(keyword for paper in papers for keyword in paper.matched_keywords)
    return [keyword for keyword, _ in counts.most_common(limit)]


def _hot_direction(papers: list[Paper]) -> str:
    counts = Counter(paper.direction for paper in papers)
    return counts.most_common(1)[0][0] if counts else "暂无"


def _rule_overview(papers: list[Paper]) -> dict[str, str]:
    if not papers:
        return {
            "main_line": "今天暂未检索到符合筛选条件的新论文。",
            "worth_attention": "暂无推荐论文。",
            "method_trend": "暂无足够信息判断方法趋势。",
            "risk_note": "建议稍后重新运行抓取流程。",
        }
    keywords = "、".join(_trend_keywords(papers)) or "暂无明显关键词"
    return {
        "main_line": f"{_hot_direction(papers)} 是今天最集中的方向，共筛选出 {len(papers)} 篇相关论文。",
        "worth_attention": f"优先阅读《{papers[0].title}》，它在今日列表中的相关性评分最高。",
        "method_trend": f"高频线索包括 {keywords}，可重点观察统一音频建模与生成能力。",
        "risk_note": "当前分析基于摘要生成。摘要未给出的实验细节、数据规模和结论边界需要阅读全文确认。",
    }


def _fallback_analysis(papers: list[Paper], deep_read_top_k: int) -> DigestAnalysis:
    return DigestAnalysis(
        overview=_rule_overview(papers),
        paper_insights={
            paper.arxiv_id: _rule_paper_insights(paper) for paper in papers[:deep_read_top_k]
        },
    )


def _client_config() -> tuple[OpenAI, str, str] | None:
    provider = os.getenv("LLM_PROVIDER", "").strip().casefold()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        return OpenAI(api_key=api_key), os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), "OpenAI"
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        return OpenAI(api_key=api_key, base_url=base_url), model, "DeepSeek"
    return None


def _prompt(papers: list[Paper], deep_read_top_k: int) -> str:
    paper_payload = [
        {
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "direction": paper.direction,
            "relevance_score": paper.relevance_score,
            "keywords": paper.matched_keywords,
            "summary": paper.summary,
        }
        for paper in papers[:deep_read_top_k]
    ]
    return f"""
你是一名谨慎的研究生论文速递编辑。请仅根据提供的论文标题、方向、关键词和摘要生成中文分析。
禁止补充摘要中没有的信息。摘要没有实验细节时，experiment_conclusion 必须写“摘要中未明确说明”。
表达要客观、具体、克制，不使用营销文案。

返回严格 JSON，不要使用 Markdown。结构必须是：
{{
  "overview": {{
    "main_line": "...",
    "worth_attention": "...",
    "method_trend": "...",
    "risk_note": "..."
  }},
  "papers": [
    {{
      "arxiv_id": "...",
      "one_sentence_summary": "...",
      "problem": "...",
      "core_method": "...",
      "innovations": "...",
      "experiment_conclusion": "...",
      "limitations": "...",
      "audience": "...",
      "related_work": "...",
      "research_inspiration": "...",
      "worth_deep_reading": "..."
    }}
  ]
}}

论文数据：
{json.dumps(paper_payload, ensure_ascii=False)}
""".strip()


def _string_fields(data: object, fields: list[str]) -> dict[str, str] | None:
    if not isinstance(data, dict):
        return None
    parsed = {}
    for field in fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return None
        parsed[field] = value.strip()
    return parsed


def _parse_analysis(
    content: str,
    papers: list[Paper],
    deep_read_top_k: int,
    source: str,
) -> DigestAnalysis | None:
    data = json.loads(content)
    overview = _string_fields(data.get("overview"), OVERVIEW_FIELDS)
    raw_papers = data.get("papers")
    if overview is None or not isinstance(raw_papers, list):
        return None

    allowed_ids = {paper.arxiv_id for paper in papers[:deep_read_top_k]}
    insights = {}
    for raw_paper in raw_papers:
        if not isinstance(raw_paper, dict) or raw_paper.get("arxiv_id") not in allowed_ids:
            continue
        parsed = _string_fields(raw_paper, PAPER_FIELDS)
        if parsed is not None:
            insights[raw_paper["arxiv_id"]] = parsed
    if not insights:
        return None
    return DigestAnalysis(overview=overview, paper_insights=insights, source=source)


def analyze_digest(papers: list[Paper], deep_read_top_k: int = 5) -> DigestAnalysis:
    load_dotenv()
    fallback = _fallback_analysis(papers, deep_read_top_k)
    config = _client_config()
    if config is None or not papers:
        return fallback

    client, model, source = config
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你只输出符合要求的 JSON。"},
                {"role": "user", "content": _prompt(papers, deep_read_top_k)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            return fallback
        parsed = _parse_analysis(content, papers, deep_read_top_k, source)
        if parsed is None:
            return fallback
        fallback.paper_insights.update(parsed.paper_insights)
        parsed.paper_insights = fallback.paper_insights
        return parsed
    except Exception as error:
        LOGGER.warning("LLM 分析失败，已降级为规则模板: %s", error)
        return fallback
