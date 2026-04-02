# FinSight Server Deployment

This guide assumes:

- Ubuntu 22.04 or similar Linux VPS
- Docker and Docker Compose plugin installed
- You want to run FinSight with Docker on a single server

## 1. Server Requirements

Recommended minimum:

- 4 vCPU
- 8 GB RAM
- 40+ GB disk

Ports used by the default stack:

- `3000` frontend
- `8000` API
- `4200` Prefect
- `9000` MinIO S3 API
- `9001` MinIO console
- `9092` Kafka

For a public deployment, you should normally expose only the frontend publicly and restrict the rest with a firewall.

## 2. Install Docker

Install Docker Engine and the Compose plugin on the server.

After install, verify:

```bash
docker --version
docker compose version
```

## 3. Copy the Project

Clone or copy the repo onto the server:

```bash
git clone <your-repo-url> finsight
cd finsight
```

## 4. Configure Environment Variables

Create a real server `.env` file.

Required values depend on the features you want enabled:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `GROQ_API_KEY`
- `TWELVE_DATA_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LOGO_DEV_PUBLISHABLE_KEY`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`

Also keep or set:

```env
TWELVE_DATA_CACHE_MINUTES=15
TELEGRAM_DAILY_BRIEF_SCHEDULE_ENABLED=true
TELEGRAM_DAILY_BRIEF_HOUR_CT=8
TELEGRAM_DAILY_BRIEF_MINUTE_CT=0
```

## 5. Build and Start

From the repo root:

For a public server, use the production override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This will build and start:

- frontend bound to `127.0.0.1:3000`
- api
- telegram-bot
- pipeline
- stream-producer
- hot-consumer
- minio
- prefect
- kafka

Important:

- in production, internal services are not published publicly
- only the frontend is bound locally on the server
- you should place Nginx or Caddy in front of it and expose only `80/443`

## 6. Verify Health

Check containers:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Check API:

```bash
curl http://localhost:8000/health
```

Check frontend:

```bash
curl -I http://localhost:3000
```

Check logs if needed:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs api --tail 100
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs frontend --tail 100
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs telegram-bot --tail 100
```

## 7. Firewall Recommendations

If this is a public VPS, restrict internal-only ports.

Public:

- `80`
- `443`

Private / restricted:

- `3000`
- `8000`
- `4200`
- `9000`
- `9001`
- `9092`

Use Nginx or Caddy in front of FinSight, expose only `80/443` publicly, and proxy to `127.0.0.1:3000`.

## 8. Updating the App

When you deploy a new version:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 9. Backups

Important state lives in Docker volumes:

- `finsight_data`
- `finsight_minio-data`
- `finsight_prefect-data`

Back up those volumes regularly if you care about:

- DuckDB data
- watchlists
- notes
- alerts
- MinIO objects

## 10. Useful Runtime Commands

Restart only frontend:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart frontend
```

Restart only API:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api
```

Rebuild frontend + API:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api frontend
```

Send a manual Telegram brief:

```bash
curl -X POST http://localhost:8000/portfolio/brief/send-telegram
```

## 11. Recommended Next Step

For a polished public deployment:

- put Nginx or Caddy in front
- terminate HTTPS there
- expose only `80/443`
- keep the API and data services private
- use the `docker-compose.prod.yml` override

## 12. Caddy Reverse Proxy

The repo includes a starter Caddy config here:

- [deploy/Caddyfile.example](c:/Users/Rajesh/Desktop/finsight/deploy/Caddyfile.example)

Use it like this on your server:

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Then:

```bash
sudo cp deploy/Caddyfile.example /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Replace:

- `your-domain.com`

with your real domain.

Make sure your DNS `A` record points to the server first.

Then restart Caddy:

```bash
sudo systemctl reload caddy
sudo systemctl status caddy
```

Caddy will automatically provision HTTPS certificates for your domain.

## 13. Production Runbook

Recommended production sequence:

1. Point your domain DNS to the VPS
2. Copy real secrets into `.env`
3. Start the app with:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

4. Install and configure Caddy
5. Verify:

```bash
curl http://127.0.0.1:3000
curl https://your-domain.com
```

6. Lock down the firewall so only:

- `22` for SSH
- `80` for HTTP
- `443` for HTTPS

are public
