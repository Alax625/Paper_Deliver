from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Paper:
    arxiv_id: str
    title: str
    summary: str
    authors: list[str]
    published: datetime
    updated: datetime
    url: str
    categories: list[str]
    relevance_score: int = 0
    matched_keywords: list[str] = field(default_factory=list)
    direction: str = "其他"
