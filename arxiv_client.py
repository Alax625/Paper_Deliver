from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from paper_model import Paper


ARXIV_API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "PaperDeliver/1.0 (arXiv API terminal digest)"


def _utc_query_range(target_date: date, timezone_name: str) -> tuple[str, str]:
    local_timezone = ZoneInfo(timezone_name)
    start_local = datetime.combine(target_date - timedelta(days=2), time.min, local_timezone)
    end_local = datetime.combine(target_date, time.max, local_timezone)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    return start_utc.strftime("%Y%m%d%H%M"), end_utc.strftime("%Y%m%d%H%M")


def _arxiv_id(entry_id: str) -> str:
    path = urlparse(entry_id).path.rstrip("/")
    return path.rsplit("/", maxsplit=1)[-1]


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _api_session() -> requests.Session:
    retry = Retry(
        total=4,
        backoff_factor=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_recent_papers(
    categories: list[str],
    max_results: int,
    target_date: date,
    timezone_name: str,
) -> list[Paper]:
    start, end = _utc_query_range(target_date, timezone_name)
    category_query = " OR ".join(f"cat:{category}" for category in categories)
    search_query = f"({category_query}) AND submittedDate:[{start} TO {end}]"
    with _api_session() as session:
        response = session.get(
            ARXIV_API_URL,
            params={
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            timeout=30,
        )
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    if feed.bozo:
        raise RuntimeError(f"无法解析 arXiv API 响应: {feed.bozo_exception}")

    papers = []
    for entry in feed.entries:
        papers.append(
            Paper(
                arxiv_id=_arxiv_id(entry.id),
                title=_clean_text(entry.title),
                summary=_clean_text(entry.summary),
                authors=[author.name for author in entry.authors],
                published=datetime.fromisoformat(entry.published.replace("Z", "+00:00")),
                updated=datetime.fromisoformat(entry.updated.replace("Z", "+00:00")),
                url=entry.id,
                categories=[tag.term for tag in entry.tags],
            )
        )
    return papers
