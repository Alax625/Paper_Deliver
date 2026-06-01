import os
import smtplib
from collections import Counter
from datetime import date
from email.message import EmailMessage
from html import escape
from urllib.parse import urljoin

from dotenv import load_dotenv

from paper_model import Paper
from summarizer import DigestAnalysis


TOP_EMAIL_COUNT = 5


def _smtp_config() -> dict[str, object] | None:
    load_dotenv()
    values = {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": os.getenv("SMTP_PORT", "").strip(),
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from": os.getenv("EMAIL_FROM", "").strip(),
        "to": os.getenv("EMAIL_TO", "").strip(),
        "base_url": os.getenv("DIGEST_BASE_URL", "").strip(),
    }
    missing = [key for key, value in values.items() if not value]
    if missing:
        print(f"邮件未发送：缺少 SMTP 配置（{', '.join(missing)}）。")
        return None
    try:
        values["port"] = int(values["port"])
    except ValueError:
        print("邮件未发送：SMTP_PORT 必须是整数。")
        return None
    values["recipients"] = [address.strip() for address in str(values["to"]).split(",") if address.strip()]
    if not values["recipients"]:
        print("邮件未发送：EMAIL_TO 未包含有效收件人。")
        return None
    return values


def _hot_direction(papers: list[Paper]) -> str:
    counts = Counter(paper.direction for paper in papers)
    return counts.most_common(1)[0][0] if counts else "暂无"


def _digest_url(base_url: str, target_date: date) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", f"{target_date.isoformat()}.html")


def _paper_url(paper: Paper) -> str:
    return f"https://arxiv.org/abs/{paper.arxiv_id}"


def _subject(title: str, target_date: date) -> str:
    return f"Paper_Deliver | {title} | {target_date.isoformat()}"


def _plain_body(
    papers: list[Paper],
    analysis: DigestAnalysis,
    digest_url: str,
) -> str:
    lines = [
        "今日统计",
        f"- 共分析论文数：{len(papers)}",
        f"- 最热门方向：{_hot_direction(papers)}",
        f"- 推荐精读数量：{min(TOP_EMAIL_COUNT, len(papers))}",
        "",
        "今日 3 分钟速览",
        f"- 今日主线：{analysis.overview['main_line']}",
        f"- 今日值得关注：{analysis.overview['worth_attention']}",
        f"- 今日方法趋势：{analysis.overview['method_trend']}",
        f"- 今日避坑提醒：{analysis.overview['risk_note']}",
        "",
        "今日必读 TOP 5",
    ]
    if papers:
        for index, paper in enumerate(papers[:TOP_EMAIL_COUNT], start=1):
            lines.append(
                f"{index}. {paper.title} | 评分 {paper.relevance_score} | "
                f"{paper.direction} | {_paper_url(paper)}"
            )
    else:
        lines.append("暂无论文。")
    lines.extend(["", f"完整网页：{digest_url}"])
    return "\n".join(lines)


def _html_body(
    title: str,
    target_date: date,
    papers: list[Paper],
    analysis: DigestAnalysis,
    digest_url: str,
) -> str:
    overview_items = [
        ("今日主线", analysis.overview["main_line"]),
        ("今日值得关注", analysis.overview["worth_attention"]),
        ("今日方法趋势", analysis.overview["method_trend"]),
        ("今日避坑提醒", analysis.overview["risk_note"]),
    ]
    overview_html = "".join(
        f"<li><strong>{escape(label)}：</strong>{escape(value)}</li>"
        for label, value in overview_items
    )
    if papers:
        top_html = "".join(
            "<li>"
            f'<a href="{escape(_paper_url(paper), quote=True)}">{escape(paper.title)}</a>'
            f" <span>评分 {paper.relevance_score} · {escape(paper.direction)}</span>"
            "</li>"
            for paper in papers[:TOP_EMAIL_COUNT]
        )
    else:
        top_html = "<li>暂无论文。</li>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<body style="margin:0;background:#f5f7fb;color:#1f2937;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;line-height:1.7;">
  <div style="max-width:720px;margin:0 auto;padding:24px;">
    <div style="padding:22px;border-radius:16px;background:#2563eb;color:#fff;">
      <h1 style="margin:0;font-size:24px;">{escape(title)}</h1>
      <p style="margin:6px 0 0;">{escape(target_date.isoformat())} · Daily Research Digest</p>
    </div>
    <div style="margin-top:16px;padding:18px;border-radius:16px;background:#fff;">
      <h2 style="margin-top:0;font-size:18px;">今日统计</h2>
      <p>共分析 <strong>{len(papers)}</strong> 篇 · 最热门方向 <strong>{escape(_hot_direction(papers))}</strong> · 推荐精读 <strong>{min(TOP_EMAIL_COUNT, len(papers))}</strong> 篇</p>
    </div>
    <div style="margin-top:16px;padding:18px;border-radius:16px;background:#fff;">
      <h2 style="margin-top:0;font-size:18px;">今日 3 分钟速览</h2>
      <ul>{overview_html}</ul>
    </div>
    <div style="margin-top:16px;padding:18px;border-radius:16px;background:#fff;">
      <h2 style="margin-top:0;font-size:18px;">今日必读 TOP 5</h2>
      <ol>{top_html}</ol>
    </div>
    <p style="margin-top:20px;text-align:center;">
      <a href="{escape(digest_url, quote=True)}" style="display:inline-block;padding:10px 18px;border-radius:999px;background:#2563eb;color:#fff;text-decoration:none;">查看完整网页</a>
    </p>
  </div>
</body>
</html>
"""


def send_digest_email(
    title: str,
    target_date: date,
    papers: list[Paper],
    analysis: DigestAnalysis,
) -> bool:
    config = _smtp_config()
    if config is None:
        return False

    digest_url = _digest_url(str(config["base_url"]), target_date)
    message = EmailMessage()
    message["Subject"] = _subject(title, target_date)
    message["From"] = str(config["from"])
    message["To"] = ", ".join(config["recipients"])
    message.set_content(_plain_body(papers, analysis, digest_url))
    message.add_alternative(_html_body(title, target_date, papers, analysis, digest_url), subtype="html")

    try:
        if config["port"] == 465:
            with smtplib.SMTP_SSL(str(config["host"]), int(config["port"]), timeout=30) as smtp:
                smtp.login(str(config["user"]), str(config["password"]))
                smtp.send_message(message)
        else:
            with smtplib.SMTP(str(config["host"]), int(config["port"]), timeout=30) as smtp:
                if config["port"] == 587:
                    smtp.starttls()
                smtp.login(str(config["user"]), str(config["password"]))
                smtp.send_message(message)
        print("邮件发送成功。")
        return True
    except Exception as error:
        print(f"邮件发送失败：{error}")
        return False
