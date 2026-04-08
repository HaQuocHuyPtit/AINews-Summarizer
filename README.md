# AInsight: Daily AI Research Digest

Hệ thống tự động tìm kiếm, tóm tắt bài báo nghiên cứu AI mới nhất và gửi email digest hàng ngày cho các thành viên trong team.

## Chức năng chính

- **Tìm kiếm bài báo** — Thu thập paper mới từ arXiv, Papers With Code, Semantic Scholar
- **Tóm tắt bằng LLM** — Sử dụng Ollama (Llama 3.1) chạy local để tóm tắt và phân loại theo chủ đề
- **Tạo digest HTML** — Tổng hợp các bản tóm tắt thành email định dạng đẹp
- **Gửi email tự động** — Gửi digest cho từng thành viên qua SMTP mỗi sáng 7h
- **Admin panel** — Giao diện Streamlit để quản lý thành viên, xem digest cũ, chạy thủ công

## Kiến trúc

```
Scheduler (APScheduler 7AM)
        │
        ▼
  LangGraph Workflow
  ┌──────────┐    ┌───────────────┐    ┌──────────────┐    ┌─────────────┐
  │ Paper    │──▶│ Paper         │──▶│ Digest       │──▶│ Email       │
  │ Searcher │    │ Summarizer    │    │ Composer     │    │ Sender      │
  └──────────┘    └───────────────┘    └──────────────┘    └─────────────┘
   arXiv API        Ollama LLM          Ollama LLM          SMTP
```

**4 Agent** được điều phối bởi **LangGraph** theo pipeline tuần tự:

| Agent | Vai trò | Kết nối ngoài |
|---|---|---|
| PaperSearcher | Tìm paper mới, lọc trùng qua Redis | arXiv, Papers With Code, Semantic Scholar |
| PaperSummarizer | Tóm tắt & phân loại từng paper | Ollama (local LLM) |
| DigestComposer | Tổng hợp thành HTML email | Ollama (local LLM) |
| EmailSender | Gửi email cho từng thành viên | SMTP server |

## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Backend API | FastAPI + Uvicorn |
| LLM Orchestration | LangChain + LangGraph |
| Local LLM | Ollama (Llama 3.1:8b) |
| Database | PostgreSQL 16 |
| Cache / Dedup | Redis 7 |
| Scheduler | APScheduler |
| Observability | Langfuse (self-hosted), structlog |
| Frontend | Streamlit |
| Email (dev) | MailHog |

## Cấu trúc thư mục

```
src/
├── main.py              # FastAPI app + lifespan
├── config.py            # Pydantic Settings (.env)
├── scheduler.py         # APScheduler cron job
├── observability.py     # Logging & tracing setup
├── agents/              # 4 agent: searcher, summarizer, composer, sender
├── api/routes.py        # REST endpoints
├── graph/workflow.py    # LangGraph workflow definition
├── models/              # SQLAlchemy models & Pydantic schemas
└── templates/           # Jinja2 email template
frontend/
└── app.py               # Streamlit admin panel
```

## Khởi chạy

```bash
# Clone & tạo file .env từ mẫu
cp .env.example .env

# Chạy toàn bộ hệ thống
docker compose up -d

# Pull model LLM
docker compose exec ollama ollama pull llama3.1:8b
```

**Truy cập:**

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Streamlit Admin | http://localhost:8501 |
| MailHog (email dev) | http://localhost:8025 |
| Langfuse | http://localhost:3000 |

## Development

```bash
# Cài dependencies
pip install -e ".[dev,frontend]"

# Chạy tests
pytest

# Lint
ruff check src/ tests/
```
