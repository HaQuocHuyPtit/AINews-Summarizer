# AInsight v2: Daily AI Research Digest

## Use Case

Every morning at 7 AM, automatically find new AI research papers, summarize them using a local LLM, and email a formatted digest to each AI dev team member.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEDULER                                │
│                   APScheduler (Daily 7 AM)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ triggers
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH WORKFLOW                             │
│                                                                 │
│  ┌──────────────┐   ┌────────────────┐   ┌─────────────────┐   │
│  │ PaperSearcher│──▶│PaperSummarizer │──▶│ DigestComposer  │   │
│  │              │   │                │   │                 │   │
│  │ • arXiv API  │   │ • Ollama       │   │ • Ollama        │   │
│  │ • Papers w/  │   │ • Summarize    │   │ • Format HTML   │   │
│  │   Code API   │   │   each paper   │   │   email digest  │   │
│  │ • Semantic   │   │ • Categorize   │   │                 │   │
│  │   Scholar    │   │   by topic     │   │                 │   │
│  └──────┬───────┘   └───────┬────────┘   └────────┬────────┘   │
│         │                   │                      │            │
│         │                   │                      ▼            │
│         │                   │              ┌───────────────┐    │
│         │                   │              │  EmailSender  │    │
│         │                   │              │               │    │
│         │                   │              │ • SMTP send   │    │
│         │                   │              │ • Per-member   │    │
│         │                   │              │ • Track status │    │
│         │                   │              └───────┬───────┘    │
└─────────┼───────────────────┼──────────────────────┼────────────┘
          │                   │                      │
          ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LOCAL INFRASTRUCTURE                         │
│                                                                 │
│  ┌────────────┐  ┌────────┐  ┌────────┐  ┌──────────────────┐  │
│  │ PostgreSQL │  │ Redis  │  │ Ollama │  │ SMTP Server      │  │
│  │            │  │        │  │        │  │                  │  │
│  │ • papers   │  │ • dedup│  │ Llama  │  │ MailHog (dev)    │  │
│  │ • digests  │  │   cache│  │ 3.1:8b │  │ Postfix (prod)   │  │
│  │ • members  │  │ • rate │  │        │  │                  │  │
│  │ • send_log │  │   limit│  │        │  │                  │  │
│  └────────────┘  └────────┘  └────────┘  └──────────────────┘  │
│                                                                 │
│  ┌──────────────────┐  ┌────────────────────────────────────┐   │
│  │ Langfuse         │  │ Streamlit Admin Panel              │   │
│  │ (self-hosted)    │  │                                    │   │
│  │ • LLM traces     │  │ • Manage team members              │   │
│  │ • Cost tracking  │  │ • View past digests                │   │
│  │ • Latency        │  │ • Trigger manual run               │   │
│  └──────────────────┘  │ • Monitor delivery status          │   │
│                        └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Graph State Flow

```
GraphState {
    papers:       List[Paper]    ← PaperSearcher fills this
    summaries:    List[Summary]  ← PaperSummarizer fills this
    digest_html:  str            ← DigestComposer fills this
    email_status: List[SendLog]  ← EmailSender fills this
}

Flow: PaperSearcher ──▶ PaperSummarizer ──▶ DigestComposer ──▶ EmailSender
```

---

## Agents

| Agent | Input | Output | External Calls |
|---|---|---|---|
| **PaperSearcher** | Empty state | `papers[]` | arXiv API, Papers With Code, Semantic Scholar |
| **PaperSummarizer** | `papers[]` | `summaries[]` | Ollama (local LLM) |
| **DigestComposer** | `summaries[]` | `digest_html` | Ollama (local LLM) |
| **EmailSender** | `digest_html` + team list from DB | `email_status[]` | SMTP server |

---

## Database Schema

```sql
CREATE TABLE team_members (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    topics      TEXT[],                          -- e.g. {"NLP", "CV", "RL"}
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE papers (
    id            SERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    authors       TEXT[],
    abstract      TEXT,
    url           VARCHAR(512) UNIQUE NOT NULL,
    source        VARCHAR(50),                   -- "arxiv", "pwc", "semantic_scholar"
    published_at  TIMESTAMP,
    fetched_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE summaries (
    id          SERIAL PRIMARY KEY,
    paper_id    INTEGER REFERENCES papers(id),
    summary     TEXT NOT NULL,
    category    VARCHAR(100),                    -- "NLP", "Computer Vision", etc.
    digest_date DATE NOT NULL
);

CREATE TABLE digests (
    id            SERIAL PRIMARY KEY,
    date          DATE UNIQUE NOT NULL,
    html_content  TEXT NOT NULL,
    paper_count   INTEGER,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE send_log (
    id         SERIAL PRIMARY KEY,
    digest_id  INTEGER REFERENCES digests(id),
    member_id  INTEGER REFERENCES team_members(id),
    status     VARCHAR(20) NOT NULL,             -- "sent", "failed", "bounced"
    sent_at    TIMESTAMP,
    error      TEXT
);
```

---

## Project Structure

```
ainsight/
├── src/
│   ├── agents/
│   │   ├── paper_searcher.py      # arXiv + PapersWithCode + SemanticScholar
│   │   ├── paper_summarizer.py    # Summarize via Ollama
│   │   ├── digest_composer.py     # Create HTML email template
│   │   └── email_sender.py        # SMTP delivery
│   ├── models/
│   │   ├── schemas.py             # Pydantic models (Paper, Summary, etc.)
│   │   └── db.py                  # SQLAlchemy ORM models
│   ├── graph/
│   │   └── workflow.py            # LangGraph state + nodes + edges
│   ├── api/
│   │   └── routes.py              # FastAPI endpoints
│   ├── templates/
│   │   └── digest.html            # Jinja2 email template
│   ├── scheduler.py               # APScheduler daily trigger
│   ├── config.py                  # pydantic-settings
│   └── main.py                    # App entrypoint
├── frontend/
│   └── app.py                     # Streamlit admin panel
├── migrations/                    # Alembic DB migrations
├── tests/
│   ├── test_searcher.py
│   ├── test_summarizer.py
│   ├── test_composer.py
│   └── test_sender.py
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.frontend
├── .env
├── .env.example
└── pyproject.toml
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Orchestration | **LangGraph** | Agent workflow with state management |
| LLM | **Ollama** (Llama 3.1:8b) | Fully local, free, no API keys |
| Paper Sources | **arXiv API** + **Semantic Scholar API** | Free, no auth required |
| Database | **PostgreSQL 16** | Papers, digests, team members, send history |
| Cache | **Redis 7** | Paper dedup, rate limiting |
| State Persistence | **LangGraph SQLite Checkpointer** | Survive crashes mid-workflow |
| Email (dev) | **MailHog** | Local catch-all SMTP with web UI |
| Email (prod) | **Postfix** or company SMTP relay | Actual email delivery |
| Email Templates | **Jinja2** | HTML email rendering |
| API | **FastAPI** | Manual triggers, team management |
| Scheduler | **APScheduler** | In-process daily cron |
| Observability | **Langfuse** (self-hosted) | LLM tracing, latency, cost |
| Admin UI | **Streamlit** | Team management, digest viewer |
| Retries | **tenacity** | Retry failed API/SMTP calls |
| ORM | **SQLAlchemy** + **Alembic** | DB access + migrations |
| Config | **pydantic-settings** | Typed config from `.env` |
| Containers | **Docker Compose** | One command to run everything |

---

## Docker Compose Services

```yaml
services:
  api:          # FastAPI + scheduler + workflow  → port 8000
  postgres:     # PostgreSQL 16                   → port 5432
  redis:        # Redis 7                         → port 6379
  ollama:       # Ollama LLM server               → port 11434
  mailhog:      # Dev email server                → port 1025 (SMTP), 8025 (Web UI)
  langfuse:     # Self-hosted tracing             → port 3000
  streamlit:    # Admin panel                     → port 8501
```

---

## Data Flow (Step by Step)

```
1. [7:00 AM] APScheduler triggers workflow.invoke()
2. PaperSearcher:
   - Queries arXiv API for papers from last 24h (cs.AI, cs.CL, cs.CV, cs.LG)
   - Queries Semantic Scholar trending papers
   - Dedup against Redis cache (skip papers seen before)
   - Stores new papers in PostgreSQL
   - Returns papers[] in state
3. PaperSummarizer:
   - For each paper, sends abstract to Ollama
   - Gets 2-3 sentence plain-English summary
   - Categorizes by topic (NLP, CV, RL, etc.)
   - Stores summaries in PostgreSQL
   - Returns summaries[] in state
4. DigestComposer:
   - Groups summaries by category
   - Renders Jinja2 HTML template with paper data
   - Asks Ollama to write an intro paragraph
   - Stores complete digest in PostgreSQL
   - Returns digest_html in state
5. EmailSender:
   - Queries active team members from PostgreSQL
   - Sends digest_html via SMTP to each member
   - Logs send status (success/fail) per member
   - Returns email_status[] in state
6. Done. Langfuse has traces for every LLM call.
```

---

## Environment Variables (.env)

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ainsight
POSTGRES_USER=ainsight
POSTGRES_PASSWORD=changeme

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# SMTP
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=ainsight@yourcompany.com
# SMTP_USER=          # uncomment for prod
# SMTP_PASSWORD=      # uncomment for prod

# Scheduler
SCHEDULE_HOUR=7
SCHEDULE_MINUTE=0

# Langfuse (optional)
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```
