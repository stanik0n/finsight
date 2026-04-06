# FinSight Project Overview

## What This Project Is

FinSight is a full-stack financial analytics platform that combines:

- a React/Vite web application
- a FastAPI backend
- a DuckDB-based analytics warehouse
- a Spark + dbt data pipeline
- real-time and batch market data workflows
- AI-assisted market analysis and portfolio workflows

The product is designed to help a user:

- monitor markets and sector signals
- analyze stocks with natural-language queries
- track a personal portfolio and watchlist
- save research notes and review triggers
- receive alerts and Telegram-based updates
- browse market news and open source articles

## What I Built

### Core product features

- Built a multi-page financial terminal-style web app with dedicated Markets, Analysis, Portfolio, and News experiences.
- Added a natural-language analysis workflow so users can ask questions about market data, portfolio context, watchlists, and news.
- Built portfolio tracking with holdings, watchlist management, research notes, alerts, and concentration insights.
- Added a news workflow with list view, article detail pages, and source links to full original articles.
- Integrated Telegram linking and bot workflows so users can connect their account and receive portfolio updates and alerts.

### UX and product work

- Reworked the app into a more intentional neobrutalist / terminal-inspired design system across pages.
- Added responsive/mobile behavior so key pages work on phones as well as desktop.
- Improved navigation by moving the app toward page-like routed views instead of a single unstable state-driven screen.
- Built a kanban-style notes board with drag-and-drop interaction for portfolio research notes.
- Added conversational fallback behavior in Analysis so the assistant can handle greetings and small talk more naturally.

### Reliability and integration work

- Fixed multiple auth, schema, and refresh issues across Portfolio, Analysis, Telegram linking, and notes save flows.
- Added graceful fallbacks for data and news retrieval so the UI stays usable when one source is thin or unavailable.
- Improved production deployment workflows with Docker Compose and server rebuild/restart patterns.

## Frontend Stack

The frontend lives in [`frontend`](c:\Users\Rajesh\Desktop\finsight\frontend) and is built with:

- React 18
- Vite
- CSS with Tailwind tooling available in the build chain
- Clerk for authentication UI and account management

### Frontend responsibilities

- render the Markets dashboard
- render the Analysis chat and session UI
- render Portfolio holdings, watchlist, alerts, and notes
- render News feed and article detail pages
- call backend endpoints for market data, query responses, portfolio state, and news
- manage authenticated and signed-out states

## Backend Stack

The backend lives in [`api`](c:\Users\Rajesh\Desktop\finsight\api) and is built with:

- Python
- FastAPI
- DuckDB
- pandas
- requests
- yfinance

### Backend responsibilities

- expose REST endpoints for market data, queries, portfolio state, news, and health
- route natural-language questions
- query DuckDB warehouse tables
- generate AI-assisted commentary
- manage saved holdings, watchlists, notes, and alerts
- manage Telegram account-linking and brief delivery flows
- serve market snapshot data for dashboards and header ticker strip

### Key backend areas

- [`api/main.py`](c:\Users\Rajesh\Desktop\finsight\api\main.py)
  Primary FastAPI app and endpoints.
- [`api/portfolio.py`](c:\Users\Rajesh\Desktop\finsight\api\portfolio.py)
  Portfolio storage, calculations, notes, alerts, and Telegram-link helpers.
- [`api/telegram_bot.py`](c:\Users\Rajesh\Desktop\finsight\api\telegram_bot.py)
  Telegram bot polling and message handling.
- [`api/hot_query.py`](c:\Users\Rajesh\Desktop\finsight\api\hot_query.py)
  Intraday / hot-path query support.
- [`api/qwen_agent.py`](c:\Users\Rajesh\Desktop\finsight\api\qwen_agent.py)
  Natural-language to query/analysis path.

## Data Pipeline and Analytics Stack

The project uses a layered data workflow:

- ingestion -> Bronze
- Spark transform -> Silver
- dbt models -> Gold
- API and UI read from Gold / latest warehouse context

### Technologies used

- Python ingestion scripts
- Kafka for streaming
- Spark for transformations
- MinIO for object storage
- PyIceberg / Iceberg-style table flow in the pipeline
- dbt for analytics modeling
- DuckDB for serving and storage
- Prefect for orchestration-related infrastructure

### Pipeline responsibilities

- ingest market data from providers
- write raw data into object storage
- compute indicators such as:
  - SMA-20
  - SMA-50
  - RSI-14
  - volume z-score
  - VWAP deviation
  - daily percent change
- load transformed rows into DuckDB-backed serving tables
- build sector, anomaly, and query-context marts for the app

### Important pipeline locations

- [`ingestion`](c:\Users\Rajesh\Desktop\finsight\ingestion)
  Batch and stream data ingestion.
- [`spark/transform.py`](c:\Users\Rajesh\Desktop\finsight\spark\transform.py)
  Rolling indicator calculations and Silver transform logic.
- [`orchestration`](c:\Users\Rajesh\Desktop\finsight\orchestration)
  Supporting scripts for alerts, delivery, and loading.
- [`dbt_finsight`](c:\Users\Rajesh\Desktop\finsight\dbt_finsight)
  dbt project for warehouse modeling.

## External APIs and Integrations

### Market and financial data

- Alpaca
  Used for market data ingestion and streaming workflows.
- Twelve Data
  Used for benchmark quote snapshots and cached live benchmark-style values.
- yfinance
  Used in backend market snapshot and ticker-strip style retrieval logic.

### AI and LLM

- Groq
  Used for model-powered commentary / AI-assisted analytical responses.

### News

- Brave News Search API
  Used to fetch finance and market news for the app's News experience.

### Auth and account management

- Clerk
  Used for sign-in, account UI, and session/auth flows.

### Messaging

- Telegram Bot API
  Used to link Telegram chats, send updates, and support bot-based interactions.

## Important Product Flows

### Markets

- market snapshot dashboard
- benchmark cards
- leaders and movers
- sector cards and volatility matrix
- market news feed
- quick analyst actions

### Analysis

- ask natural-language market and portfolio questions
- route between live, historical, hybrid, and portfolio-aware responses
- show recent sessions
- support conversational fallback for greetings and small talk

### Portfolio

- add and manage holdings
- maintain a watchlist
- calculate total value, cost basis, P&L, and concentration
- store structured notes
- organize notes into kanban-style lanes
- generate and display portfolio alerts

### News

- show a dedicated feed of current articles
- open article detail view
- link out to the original publication

### Telegram

- link Telegram to a signed-in user
- support code/deep-link based linking flows
- send alerts and daily portfolio briefs

## Authentication and User Data

The project supports signed-in user flows with Clerk and stores user-scoped data in DuckDB tables such as:

- `app.user_portfolio_holdings`
- `app.user_portfolio_watchlist`
- `app.user_ticker_notes`
- `app.user_portfolio_alerts`
- `app.user_portfolio_alert_preferences`

This allows the app to keep:

- portfolio data
- watchlists
- notes
- alerts
- Telegram link state

scoped per signed-in user rather than only globally.

## Infrastructure and Deployment

The app is containerized with Docker Compose and includes services for:

- frontend
- api
- telegram-bot
- pipeline
- stream-producer
- hot-consumer
- kafka
- minio
- prefect

### Deployment model

The repo includes:

- [`docker-compose.yml`](c:\Users\Rajesh\Desktop\finsight\docker-compose.yml)
  Base multi-service environment.
- [`docker-compose.dev.yml`](c:\Users\Rajesh\Desktop\finsight\docker-compose.dev.yml)
  Development overrides.
- [`docker-compose.prod.yml`](c:\Users\Rajesh\Desktop\finsight\docker-compose.prod.yml)
  Production-safe overrides.
- [`DEPLOY_SERVER.md`](c:\Users\Rajesh\Desktop\finsight\DEPLOY_SERVER.md)
  Server deployment guide.

### Runtime storage

Persistent application state is kept in Docker volumes for:

- DuckDB databases
- MinIO data
- Prefect state

## Technical Highlights

- Built a hybrid analytics app that combines traditional data engineering with an AI query layer.
- Used DuckDB as both a practical serving layer and an analytics storage engine.
- Combined batch, streaming, warehouse, and product-facing API patterns in one deployable project.
- Added user-level persistence for portfolio features inside an analytics-focused application.
- Integrated external systems including auth, Telegram, market-data vendors, and news search.
- Shipped both product features and production operations patterns in one codebase.

## Resume-Ready Summary

### Short version

Built FinSight, a full-stack financial analytics platform with React/Vite, FastAPI, DuckDB, Spark, dbt, Kafka, and Docker Compose, supporting AI-assisted market analysis, portfolio tracking, news aggregation, alerts, and Telegram integrations.

### Resume bullet ideas

- Built a full-stack financial analytics platform using React/Vite, FastAPI, DuckDB, Spark, dbt, Kafka, and Docker Compose, supporting market dashboards, portfolio tracking, notes, alerts, and news workflows.
- Implemented AI-assisted natural-language analysis across live, historical, news, watchlist, and portfolio contexts, with query routing and generated market commentary.
- Integrated external services including Clerk authentication, Brave News Search, Alpaca/Twelve market data, and Telegram bot workflows for account linking and alert delivery.

## Interview Talking Points

If you need to explain this project in an interview, strong angles are:

- product architecture
  You built a user-facing financial product, not just a dashboard.
- data engineering
  You handled ingestion, transformation, warehouse modeling, and serving.
- full-stack ownership
  You worked across frontend UX, backend APIs, data storage, and deployment.
- integrations
  You connected auth, messaging, market data, and news into one system.
- debugging and production thinking
  You dealt with auth mismatches, schema evolution, data backfills, API fallbacks, and deployment issues.

## Good One-Line Description

FinSight is an AI-assisted financial terminal and portfolio intelligence platform that combines market data pipelines, a DuckDB analytics warehouse, natural-language analysis, portfolio tracking, news aggregation, and Telegram alerting in a production-style full-stack application.
