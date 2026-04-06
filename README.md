# FinSight

FinSight is a full-stack financial analytics platform that combines market dashboards, AI-assisted analysis, portfolio tracking, news aggregation, and Telegram delivery into a single product.

It is built as a production-style system with:

- a React + Vite frontend
- a FastAPI backend
- a DuckDB analytics warehouse
- Spark and dbt data pipelines
- Kafka-based streaming support
- Docker Compose deployment

## What It Does

### Markets

- shows benchmark and sector-level market context
- surfaces leaders, laggards, and volatility signals
- displays curated market news from Brave News Search
- supports a live-style header ticker strip

### Analysis

- accepts natural-language questions about markets, portfolio state, watchlists, and news
- routes questions across live, historical, hybrid, and portfolio-aware paths
- returns analyst-style commentary instead of raw data only

### Portfolio

- tracks holdings and watchlist symbols
- calculates value, P&L, concentration, and signal summaries
- stores structured research notes
- organizes notes into kanban-style lanes
- generates alerts and supports Telegram brief delivery

### News

- shows a dedicated market news feed
- opens article detail pages
- links out to the original publication

## Architecture

```text
Frontend (React/Vite)
    ->
FastAPI API
    ->
DuckDB serving layer / market snapshot endpoints
    ->
Batch + stream data pipeline
    ->
MinIO + Kafka + Spark + dbt
```

### High-level flow

1. Market data is ingested in batch and stream workflows.
2. Spark computes derived indicators such as RSI, SMA, volume z-score, and percent change.
3. dbt models shape analytics tables for the app.
4. FastAPI exposes those results through product-facing endpoints.
5. React renders dashboards, analysis, portfolio workflows, and news.

## Tech Stack

### Frontend

- React 18
- Vite
- Clerk authentication
- CSS / Tailwind build tooling

### Backend

- Python
- FastAPI
- DuckDB
- pandas
- yfinance

### Data and orchestration

- Kafka
- Spark
- MinIO
- dbt
- Prefect

### Integrations

- Alpaca market data
- Twelve Data benchmark quotes
- Brave News Search API
- Telegram Bot API
- Clerk auth

## Project Structure

```text
api/              FastAPI app, portfolio logic, auth, Telegram bot
frontend/         React app and UI
ingestion/        Batch and streaming ingestion jobs
spark/            Indicator transforms
orchestration/    Load, alert, and delivery scripts
dbt_finsight/     Analytics models and seeds
pipeline/         Containerized pipeline runtime
deploy/           Reverse proxy and deployment helpers
```

## Key Features

- AI-assisted market analysis
- market snapshot dashboard
- portfolio tracking and watchlist management
- kanban-style research notes
- alert generation and Telegram delivery
- dedicated news feed and article detail flow
- responsive/mobile-friendly product UI

## Local Development

### Prerequisites

- Docker
- Docker Compose plugin
- Node.js 20+ if running the frontend outside Docker
- Python 3.11+ if running services locally outside Docker

### Environment setup

Copy the example environment file and fill in your real credentials:

```bash
cp .env.example .env
```

Important:

- do not commit `.env`
- use placeholder values only in `.env.example`

### Run with Docker

For local development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

For a production-style local run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Important Environment Variables

See [`.env.example`](./.env.example) for the full list.

Common ones include:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `GROQ_API_KEY`
- `TWELVE_DATA_API_KEY`
- `BRAVE_SEARCH_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `VITE_CLERK_PUBLISHABLE_KEY`
- `CLERK_JWT_PUBLIC_KEY`
- `FINSIGHT_INTERNAL_API_KEY`

## Deployment

The project is designed to be deployed with Docker Compose behind a reverse proxy.

Helpful files:

- [DEPLOY_SERVER.md](./DEPLOY_SERVER.md)
- [deploy/Caddyfile.example](./deploy/Caddyfile.example)
- [docker-compose.prod.yml](./docker-compose.prod.yml)

## Product Highlights

- built a real user-facing financial product instead of a demo dashboard
- combined AI, analytics engineering, and full-stack application work
- integrated auth, messaging, market data, and news into one deployable system
- designed for both interactive product use and production-style operations

## Resume Summary

Built FinSight, a full-stack financial analytics platform using React, FastAPI, DuckDB, Spark, dbt, Kafka, and Docker Compose, with AI-assisted analysis, portfolio tracking, news aggregation, and Telegram alerts.

## Additional Documentation

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)
- [DEPLOY_SERVER.md](./DEPLOY_SERVER.md)

## Security Notes

- `.env` is intentionally ignored
- `.env.example` contains placeholders only
- local editor and tool metadata is ignored
- certificate and key files are ignored by default
