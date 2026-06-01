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
python main.py --send-email
python main.py --no-email --ignore-seen
python main.py --date 2026-06-01
```

- `python main.py`：打印尚未处理的论文，并把本次抓到的 arXiv ID 写入 `seen_papers.json`。
- `python main.py --dry-run`：打印查询结果，不读取去重结果进行过滤，也不修改 `seen_papers.json`。
- `python main.py --no-email`：打印尚未处理的论文，生成 `outputs/YYYY-MM-DD.md`、`docs/YYYY-MM-DD.html` 和 `docs/index.html`，并更新去重记录。
- `python main.py --send-email`：生成日报网页，并尝试发送精简邮件提醒。
- `python main.py --no-email --ignore-seen`：忽略 `seen_papers.json`，使用当日抓取结果重新处理并生成网页。
- `python main.py --date YYYY-MM-DD`：指定 3 天查询窗口的截止日期。

检索类别、结果数量、关键词、时区和标题可以在 `config.yaml` 中修改。

## 大模型中文分析

项目支持使用 OpenAI 或 DeepSeek 为今日速览和精读卡片生成中文分析。默认只分析
`config.yaml` 中 `deep_read_top_k` 指定的前几篇论文，默认值为 `5`。

在项目根目录创建 `.env` 文件。使用 OpenAI：

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
```

使用 DeepSeek：

```dotenv
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

DeepSeek 通过 OpenAI SDK 兼容模式调用。未配置 API Key、API 调用失败或模型返回内容
无法解析时，程序会自动降级为规则模板，仍然可以正常生成 Markdown 和 HTML。

## SMTP 邮件提醒

在项目根目录的 `.env` 中增加 SMTP 配置：

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
EMAIL_FROM=paper-deliver@example.com
EMAIL_TO=recipient@example.com
DIGEST_BASE_URL=https://example.com/paper-deliver/
```

`EMAIL_TO` 可以使用逗号分隔多个收件人。`SMTP_PORT=465` 时使用 `SMTP_SSL`，
`SMTP_PORT=587` 时使用 `SMTP + starttls`。缺少 SMTP 配置或发送失败时，程序只打印提示，
不会影响 Markdown 和 HTML 日报生成。
