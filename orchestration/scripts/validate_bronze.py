"""
Validates the Bronze Parquet file for a given date:
- File exists in MinIO
- Row count > 0
- No nulls in close or volume
- Expected tickers present
"""

import os
import sys
import yaml
from datetime import date, timedelta
from io import BytesIO

import boto3
import pandas as pd


def load_tickers() -> list[str]:
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'tickers.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return [t for sector in config['sectors'].values() for t in sector]


def validate(target_date: date) -> None:
    s3 = boto3.client(
        's3',
        endpoint_url=os.environ['MINIO_ENDPOINT'],
        aws_access_key_id=os.environ['MINIO_ACCESS_KEY'],
        aws_secret_access_key=os.environ['MINIO_SECRET_KEY'],
    )
    bucket = os.environ.get('S3_BUCKET', 'finsight')
    key = f"bronze/bars/date={target_date}/batch.parquet"

    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_parquet(BytesIO(resp['Body'].read()))
    except Exception as e:
        raise RuntimeError(f"[validate] Cannot read Bronze file {key}: {e}")

    errors = []

    if df.empty:
        errors.append("Bronze file is empty")
    else:
        null_close = df['close'].isnull().sum()
        null_volume = df['volume'].isnull().sum()
        if null_close > 0:
            errors.append(f"{null_close} null values in 'close'")
        if null_volume > 0:
            errors.append(f"{null_volume} null values in 'volume'")

        expected = set(load_tickers())
        got = set(df['symbol'].unique())
        missing = expected - got
        if len(missing) > 5:
            errors.append(f"{len(missing)} tickers missing from Bronze: {sorted(missing)[:10]}...")

    if errors:
        raise ValueError(f"[validate] Bronze validation failed for {target_date}:\n" + "\n".join(f"  - {e}" for e in errors))

    print(f"[validate] OK - {len(df)} rows, {df['symbol'].nunique()} tickers for {target_date}")


if __name__ == '__main__':
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today() - timedelta(days=1)
    validate(target)
