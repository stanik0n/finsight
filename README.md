# FinSight

An AI-assisted financial analytics platform that combines market dashboards, portfolio intelligence, structured research notes, curated news, and Telegram delivery in one full-stack product.

![React](https://img.shields.io/badge/React-Frontend-61dafb?style=flat-square&logo=react&logoColor=white)
![Python](https://img.shields.io/badge/Python-Backend-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-Warehouse-f7c948?style=flat-square)
![Apache Kafka](https://img.shields.io/badge/Kafka-Streaming-231f20?style=flat-square&logo=apachekafka&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Spark-Processing-e25a1c?style=flat-square&logo=apachespark&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-Modeling-ff694b?style=flat-square&logo=dbt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker&logoColor=white)

## Demo

**Live:** https://finsight.rajeshchowdary.com

---

## Architecture

```text
Alpaca / Twelve Data / Brave News / yfinance
                    │
                    ▼
      Ingestion + streaming jobs (Python)
                    │
                    ├──▶ Kafka                  intraday stream transport
                    ├──▶ MinIO                  raw / warehouse object storage
                    └──▶ Spark transform        RSI, SMA, VWAP, pct_change, z-score
                                │
                                ▼
                        dbt + DuckDB warehouse
                                │
                                ▼
                     FastAPI application layer
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
          React + Vite      Clerk auth      Telegram bot
```

---

## Features

- **Market overview** — benchmark context, sector summaries, movers, volatility signals, and a live-style ticker strip
- **AI-assisted analysis** — natural-language questions across live, historical, hybrid, news, watchlist, and portfolio contexts
- **Portfolio tracking** — saved holdings, watchlist, P&L, concentration profile, top winner/loser, and signal summaries
- **Research notes board** — kanban-style note management for thesis, risk rules, review notes, exit triggers, and general notes
- **News aggregation** — Brave News Search-backed market news feed with source article pages and external links
- **Telegram integration** — account linking, portfolio briefs, and alert delivery through a Telegram bot
- **Responsive product UI** — mobile-friendly layouts across Markets, Analysis, Portfolio, and News

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI (Python) |
| Analytics warehouse | DuckDB |
| Batch transform | Spark |
| Modeling layer | dbt |
| Streaming | Kafka |
| Object storage | MinIO |
| Auth | Clerk |
| News | Brave News Search API |
| Market data | Alpaca, Twelve Data, yfinance |
| Messaging | Telegram Bot API |
| Deployment | Docker Compose |

---

## Getting Started

### Prerequisites

- Docker + Docker Compose plugin
- Node.js 20+ if you want to run the frontend outside Docker
- Python 3.11+ if you want to run services outside Docker

### Setup

```bash
git clone <your-repo-url> finsight
cd finsight

cp .env.example .env
# Fill in the environment variables you want to enable
```

### Run

For local development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

For a production-style run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The frontend will be available through the configured frontend service and proxy setup.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ALPACA_API_KEY` | No | Batch and streaming market data ingestion |
| `ALPACA_SECRET_KEY` | No | Batch and streaming market data ingestion |
| `TWELVE_DATA_API_KEY` | No | Benchmark quote snapshots |
| `BRAVE_SEARCH_API_KEY` | No | Market and business news retrieval |
| `GROQ_API_KEY` | No | AI-assisted commentary / analysis generation |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot integration |
| `TELEGRAM_BOT_USERNAME` | No | Telegram deep-link / linking flow |
| `VITE_CLERK_PUBLISHABLE_KEY` | No | Frontend authentication |
| `CLERK_JWT_PUBLIC_KEY` | No | Backend token validation |
| `FINSIGHT_INTERNAL_API_KEY` | No | Internal service auth between app services |
| `MINIO_ROOT_USER` | No | MinIO object storage username |
| `MINIO_ROOT_PASSWORD` | No | MinIO object storage password |

See [`.env.example`](./.env.example) for the full configuration.

---

## Project Structure

```text
finsight/
├── api/              FastAPI app, auth, portfolio logic, Telegram bot
├── frontend/         React app, routes, pages, components, styles
├── ingestion/        Batch and stream market data ingestion
├── spark/            Indicator transform pipeline
├── orchestration/    Load, alert, and delivery scripts
├── dbt_finsight/     Warehouse models, marts, seeds
├── pipeline/         Container runtime for pipeline jobs
├── prefect/          Prefect container setup
├── deploy/           Reverse proxy and deployment helpers
└── config/           Project config such as tracked ticker metadata
```

---

## How It Works

1. **Ingestion** pulls market data from configured providers and writes raw data into the pipeline flow.

2. **Streaming and batch processing** move data through Kafka and Spark, where rolling indicators like RSI, SMA, VWAP deviation, volume z-score, and daily percent change are computed.

3. **dbt models** transform the warehouse into serving-friendly marts for:
   - market snapshot
   - sector summaries
   - anomaly detection
   - query context

4. **FastAPI** exposes product endpoints for:
   - `/market-snapshot`
   - `/market-news`
   - `/query`
   - `/portfolio`
   - `/notes`
   - `/telegram`

5. **React frontend** renders the product experience across:
   - Markets
   - Analysis
   - Portfolio
   - News

6. **Telegram bot flows** allow account linking and delivery of alerts and portfolio summaries outside the web app.

---

## Additional Documentation

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)
- [DEPLOY_SERVER.md](./DEPLOY_SERVER.md)
- [deploy/Caddyfile.example](./deploy/Caddyfile.example)

---

## Security Notes

- `.env` is ignored by Git
- `.env.example` contains placeholders only
- local secret files and key/certificate files are ignored
- local editor and tool metadata is ignored by default
