# FinSight

An AI-assisted financial analytics platform that combines market dashboards, portfolio intelligence, structured research notes, curated news, and Telegram delivery in one full-stack product.

![React](https://img.shields.io/badge/React-Frontend-61dafb?style=flat-square&logo=react&logoColor=white)
![Python](https://img.shields.io/badge/Python-Backend-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-Warehouse-f7c948?style=flat-square)
![Apache Kafka](https://img.shields.io/badge/Kafka-Streaming-231f20?style=flat-square&logo=apachekafka&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Spark-Processing-e25a1c?style=flat-square&logo=apachespark&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-Modeling-ff694b?style=flat-square&logo=dbt&logoColor=white)
![Qwen](https://img.shields.io/badge/Qwen-Query%20Layer-7c3aed?style=flat-square)
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
                                ├──▶ Qwen-style text-to-SQL / analysis layer
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
          React + Vite      Clerk auth      Telegram bot
```

---

## Features

- **Market overview** - benchmark context, sector summaries, movers, volatility signals, and a live-style ticker strip
- **AI-assisted analysis** - natural-language questions across live, historical, hybrid, news, watchlist, and portfolio contexts through a Qwen-based query layer
- **Portfolio tracking** - saved holdings, watchlist, P&L, concentration profile, top winner/loser, and signal summaries
- **Research notes board** - kanban-style note management for thesis, risk rules, review notes, exit triggers, and general notes
- **News aggregation** - Brave News Search-backed market news feed with source article pages and external links
- **Telegram integration** - account linking, portfolio briefs, and alert delivery through a Telegram bot
- **Responsive product UI** - mobile-friendly layouts across Markets, Analysis, Portfolio, and News

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI (Python) |
| LLM query layer | Qwen-oriented text-to-SQL flow via Groq |
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

## Product Areas

### Markets

- market overview
- benchmark cards
- quick actions
- watchlist
- sector summaries
- market news

### Analysis

- natural-language financial Q&A
- historical and live market context
- portfolio-aware responses
- recent-session continuity

### Portfolio

- saved holdings
- watchlist management
- alert summaries
- research notes board
- concentration and winner/loser views

### News

- dedicated news feed
- article detail pages
- links to original sources

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
└── config/           Project config and tracked market metadata
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

4. **Qwen query logic** converts natural-language analytical questions into structured query behavior inside the backend analysis flow.

5. **FastAPI** exposes product endpoints for:
   - `/market-snapshot`
   - `/market-news`
   - `/query`
   - `/portfolio`
   - `/notes`
   - `/telegram`

6. **React frontend** renders the product experience across:
   - Markets
   - Analysis
   - Portfolio
   - News

7. **Telegram bot flows** extend the product outside the web app through account linking and delivery workflows.
