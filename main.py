import argparse
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from arxiv_client import fetch_recent_papers
from classifier import classify_paper
from paper_model import Paper
from renderer import write_digest_files
from scorer import score_paper


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
SEEN_PAPERS_PATH = BASE_DIR / "seen_papers.json"
AUDIO_CATEGORIES = {"eess.AS", "cs.SD"}
AMBIGUOUS_KEYWORDS = {"speech", "voice"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取并打印近期语音、音乐、音频相关 arXiv 论文")
    parser.add_argument("--dry-run", action="store_true", help="仅打印论文，不更新 seen_papers.json")
    parser.add_argument("--no-email", action="store_true", help="生成 Markdown 和 HTML，不发送邮件")
    parser.add_argument("--ignore-seen", action="store_true", help="忽略 seen_papers.json，重新处理已见论文")
    parser.add_argument("--date", type=date.fromisoformat, help="指定查询截止日期，格式为 YYYY-MM-DD")
    return parser.parse_args()


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    required = ["categories", "max_results", "top_k", "keywords", "timezone", "digest_title"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"config.yaml 缺少配置项: {', '.join(missing)}")
    return config


def load_seen_papers() -> set[str]:
    if not SEEN_PAPERS_PATH.exists():
        return set()
    with SEEN_PAPERS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("seen_papers.json 必须是 JSON 数组")
    return set(data)


def save_seen_papers(seen_papers: set[str]) -> None:
    with SEEN_PAPERS_PATH.open("w", encoding="utf-8") as file:
        json.dump(sorted(seen_papers), file, ensure_ascii=False, indent=2)
        file.write("\n")


def prepare_papers(papers: list[Paper], keywords: list[str]) -> list[Paper]:
    relevant_papers = []
    for paper in papers:
        paper.relevance_score, paper.matched_keywords = score_paper(paper, keywords)
        paper.direction = classify_paper(paper)
        has_audio_category = bool(AUDIO_CATEGORIES.intersection(paper.categories))
        has_specific_keyword = any(
            keyword.casefold() not in AMBIGUOUS_KEYWORDS for keyword in paper.matched_keywords
        )
        if paper.relevance_score > 0 and (has_audio_category or has_specific_keyword):
            relevant_papers.append(paper)
    return sorted(relevant_papers, key=lambda paper: (-paper.relevance_score, -paper.published.timestamp()))


def print_digest(title: str, papers: list[Paper], target_date: date, dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "正式运行"
    print(f"\n{title}")
    print(f"日期：{target_date.isoformat()} | 模式：{mode} | 论文数：{len(papers)}")
    print("=" * 72)
    if not papers:
        print("没有符合条件的新论文。")
        return

    for index, paper in enumerate(papers, start=1):
        print(f"\n[{index}] {paper.title}")
        print(f"作者：{', '.join(paper.authors)}")
        print(f"发布时间：{paper.published.isoformat()}")
        print(f"arXiv ID：{paper.arxiv_id}")
        print(f"链接：https://arxiv.org/abs/{paper.arxiv_id}")
        print(f"方向分类：{paper.direction}")
        print(f"相关性评分：{paper.relevance_score}")
        print("摘要：")
        print(paper.summary)
        print("-" * 72)


def main() -> None:
    args = parse_args()
    config = load_config()
    timezone = ZoneInfo(config["timezone"])
    target_date = args.date or datetime.now(timezone).date()
    papers = fetch_recent_papers(
        categories=config["categories"],
        max_results=config["max_results"],
        target_date=target_date,
        timezone_name=config["timezone"],
    )
    seen_papers = load_seen_papers()
    ranked_papers = prepare_papers(papers, config["keywords"])
    page_papers = ranked_papers[: config["top_k"]]
    if args.dry_run or args.ignore_seen:
        selected_papers = page_papers
    else:
        selected_papers = [
            paper for paper in ranked_papers if paper.arxiv_id not in seen_papers
        ][: config["top_k"]]
    print_digest(config["digest_title"], selected_papers, target_date, args.dry_run)

    if args.no_email:
        markdown_path, html_path, index_path = write_digest_files(
            config["digest_title"], page_papers, target_date, config.get("deep_read_top_k", 5)
        )
        print("\n已生成文件：")
        print(f"- {markdown_path.relative_to(BASE_DIR)}")
        print(f"- {html_path.relative_to(BASE_DIR)}")
        print(f"- {index_path.relative_to(BASE_DIR)}")

    if not args.dry_run:
        seen_papers.update(paper.arxiv_id for paper in papers)
        save_seen_papers(seen_papers)


if __name__ == "__main__":
    main()
