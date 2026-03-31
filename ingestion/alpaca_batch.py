"""
Batch ingestion: pulls previous day's OHLCV bars for all 50 tickers from Alpaca
and writes raw Parquet to Bronze layer on MinIO.

Usage:
    python alpaca_batch.py              # defaults to yesterday
    python alpaca_batch.py 2024-03-15   # specific date
"""

import os
import sys
import yaml
from datetime import date, timedelta
from io import BytesIO

import boto3
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame


def load_tickers() -> list[str]:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tickers.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return [ticker for sector in config['sectors'].values() for ticker in sector]


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ['MINIO_ENDPOINT'],
        aws_access_key_id=os.environ['MINIO_ACCESS_KEY'],
        aws_secret_access_key=os.environ['MINIO_SECRET_KEY'],
    )


def fetch_bars(target_date: date) -> pd.DataFrame:
    tickers = load_tickers()
    client = StockHistoricalDataClient(
        api_key=os.environ['ALPACA_API_KEY'],
        secret_key=os.environ['ALPACA_SECRET_KEY'],
    )

    request = StockBarsRequest(
        symbol_or_symbols=tickers,
        timeframe=TimeFrame.Day,
        start=target_date,
        end=target_date + timedelta(days=1),
        adjustment='split',
    )

    bars = client.get_stock_bars(request)
    df = bars.df

    if df.empty:
        return df

    # Reset multi-index (symbol, timestamp) to flat columns
    df = df.reset_index()
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    return df


def write_to_bronze(df: pd.DataFrame, target_date: date) -> None:
    s3 = get_s3_client()
    bucket = os.environ.get('S3_BUCKET', 'finsight')
    key = f"bronze/bars/date={target_date}/batch.parquet"

    buffer = BytesIO()
    df.to_parquet(buffer, index=False, engine='pyarrow')
    buffer.seek(0)

    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
    print(f"[bronze] Written {len(df)} rows → s3://{bucket}/{key}")


def run(target_date: date = None) -> None:
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    print(f"[ingestion] Fetching bars for {target_date}")
    df = fetch_bars(target_date)

    if df.empty:
        print(f"[ingestion] No data for {target_date} — likely a non-trading day. Exiting.")
        sys.exit(0)

    write_to_bronze(df, target_date)
    print(f"[ingestion] Done. {len(df['symbol'].unique())} tickers ingested.")


if __name__ == '__main__':
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(target)
