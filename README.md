# Paper_Deliver

从 arXiv API 抓取最近 3 天的语音、音乐和音频相关论文，在终端打印结果，并生成 Markdown 和 HTML 日报。

## 安装

```powershell
pip install -r requirements.txt
```

## 使用

```powershell
python main.py
python main.py --dry-run
python main.py --no-email
python main.py --no-email --ignore-seen
python main.py --date 2026-06-01
```

- `python main.py`：打印尚未处理的论文，并把本次抓到的 arXiv ID 写入 `seen_papers.json`。
- `python main.py --dry-run`：打印查询结果，不读取去重结果进行过滤，也不修改 `seen_papers.json`。
- `python main.py --no-email`：打印尚未处理的论文，生成 `outputs/YYYY-MM-DD.md`、`docs/YYYY-MM-DD.html` 和 `docs/index.html`，并更新去重记录。
- `python main.py --no-email --ignore-seen`：忽略 `seen_papers.json`，使用当日抓取结果重新处理并生成网页。
- `python main.py --date YYYY-MM-DD`：指定 3 天查询窗口的截止日期。

检索类别、结果数量、关键词、时区和标题可以在 `config.yaml` 中修改。
