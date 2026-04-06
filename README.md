<div align="center">

# FinSight

### AI-assisted financial analytics platform for markets, portfolio intelligence, and news workflows

[Overview](#overview) •
[Features](#features) •
[Architecture](#architecture) •
[Tech Stack](#tech-stack) •
[Getting Started](#getting-started) •
[Deployment](#deployment)

</div>

---

## Overview

FinSight is a full-stack financial analytics product built to combine:

- market dashboards
- natural-language financial analysis
- portfolio and watchlist tracking
- structured research notes
- market news aggregation
- Telegram-based alerts and brief delivery

It is designed like a lightweight financial terminal with product-facing UX on top of a real analytics stack.

## Features

### Market intelligence

- benchmark and sector-level market overview
- movers, laggards, and volatility snapshots
- live-style header ticker strip
- market news feed with source article links

### Analysis workspace

- ask market and portfolio questions in natural language
- route questions across live, historical, hybrid, and portfolio-aware contexts
- receive analyst-style commentary instead of raw tables alone

### Portfolio workflows

- track holdings and watchlist symbols
- calculate value, P&L, and concentration
- generate portfolio alerts
- manage research notes in a kanban-style board

### Messaging and delivery

- Telegram account linking
- Telegram bot workflows
- portfolio brief and alert delivery

## Architecture

```text
React + Vite frontend
        ↓
FastAPI application layer
        ↓
DuckDB serving + analytics layer
        ↓
Spark + dbt transformation pipeline
        ↓
MinIO / Kafka / ingestion services
```

### Data flow

1. Market data is ingested through batch and streaming workflows.
2. Spark computes indicators such as RSI, SMA, VWAP deviation, volume z-score, and daily percent change.
3. dbt models build serving-ready marts for the application.
4. FastAPI exposes product endpoints for dashboards, analysis, portfolio state, and news.
5. React renders the user experience across Markets, Analysis, Portfolio, and News.

## Tech Stack

### Frontend

- React 18
- Vite
- Clerk authentication
- CSS-based terminal/neobrutalist UI system

### Backend

- Python
- FastAPI
- DuckDB
- pandas
- yfinance

### Data platform

- Kafka
- Spark
- dbt
- MinIO
- Prefect

### Integrations

- Alpaca market data
- Twelve Data benchmark quotes
- Brave News Search API
- Telegram Bot API
- Clerk auth

## Repository Structure

```text
api/              FastAPI app, auth, portfolio logic, Telegram bot
frontend/         React app, routes, pages, components, styling
ingestion/        Batch and streaming market data ingestion
spark/            Indicator transforms and Silver build logic
orchestration/    Load, validation, alert, and delivery scripts
dbt_finsight/     Analytics models and warehouse marts
pipeline/         Container runtime for pipeline jobs
deploy/           Reverse proxy and deployment helpers
```

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
- recent session memory

### Portfolio

- saved holdings
- watchlist management
- alert summaries
- research notes board
- concentration and winner/loser views

### News

- dedicated news feed
- article detail pages
- full source links

## Getting Started

### Prerequisites

- Docker
- Docker Compose plugin
- Node.js 20+ for standalone frontend development
- Python 3.11+ for standalone backend development

### Environment

Create a local environment file from the example:

```bash
cp .env.example .env
```

Then fill in the credentials you want to enable.

Common integrations:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `GROQ_API_KEY`
- `TWELVE_DATA_API_KEY`
- `BRAVE_SEARCH_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `VITE_CLERK_PUBLISHABLE_KEY`
- `CLERK_JWT_PUBLIC_KEY`

See [`.env.example`](./.env.example) for the full list.

### Local development

Run the full local stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Run a production-style local stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Deployment

FinSight is designed to run through Docker Compose behind a reverse proxy.

Helpful deployment files:

- [DEPLOY_SERVER.md](./DEPLOY_SERVER.md)
- [deploy/Caddyfile.example](./deploy/Caddyfile.example)
- [docker-compose.prod.yml](./docker-compose.prod.yml)

Typical update flow:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Highlights

- full-stack financial product, not just a dashboard prototype
- analytics pipeline and user-facing app in one system
- AI-assisted financial analysis across live, historical, and portfolio contexts
- real portfolio notes, alerts, and messaging workflows
- production-style containerized deployment

## Documentation

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)
- [DEPLOY_SERVER.md](./DEPLOY_SERVER.md)

## Security Notes

- `.env` is ignored
- `.env.example` contains placeholders only
- local secrets, certificate files, and editor/tool metadata are ignored by default

---

## Resume Summary

Built FinSight, a full-stack financial analytics platform using React, FastAPI, DuckDB, Spark, dbt, Kafka, and Docker Compose, with AI-assisted analysis, portfolio tracking, news aggregation, and Telegram alerts.
