"""
PySpark transform: reads Bronze Parquet from MinIO (60-day window),
computes SMA-20/50, RSI-14, volume z-score, VWAP deviation, daily % change,
then writes the target date's rows to Silver Iceberg via PyIceberg.

Runs in local[*] mode - no Spark cluster needed.
"""

import os
import sys
from datetime import date, timedelta
from io import BytesIO

import boto3
import pandas as pd
import pyarrow as pa
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.partitioning import PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

SILVER_TABLE = 'silver.stock_metrics'

SILVER_SCHEMA = Schema(
    NestedField(1, 'symbol', StringType(), required=False),
    NestedField(2, 'date', DateType(), required=False),
    NestedField(3, 'open', DoubleType(), required=False),
    NestedField(4, 'high', DoubleType(), required=False),
    NestedField(5, 'low', DoubleType(), required=False),
    NestedField(6, 'close', DoubleType(), required=False),
    NestedField(7, 'volume', LongType(), required=False),
    NestedField(8, 'vwap', DoubleType(), required=False),
    NestedField(9, 'sma_20', DoubleType(), required=False),
    NestedField(10, 'sma_50', DoubleType(), required=False),
    NestedField(11, 'rsi_14', DoubleType(), required=False),
    NestedField(12, 'volume_zscore', DoubleType(), required=False),
    NestedField(13, 'vwap_deviation', DoubleType(), required=False),
    NestedField(14, 'pct_change', DoubleType(), required=False),
    NestedField(15, 'ingested_at', TimestampType(), required=False),
)

SILVER_PARTITION_SPEC = PartitionSpec()


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ['MINIO_ENDPOINT'],
        aws_access_key_id=os.environ['MINIO_ACCESS_KEY'],
        aws_secret_access_key=os.environ['MINIO_SECRET_KEY'],
    )


def get_iceberg_catalog() -> SqlCatalog:
    return SqlCatalog(
        'finsight',
        **{
            'uri': f'sqlite:////{os.environ.get("DUCKDB_PATH", "/data/finsight.duckdb").replace("finsight.duckdb", "iceberg_catalog.db")}',
            'warehouse': f's3://{os.environ.get("S3_BUCKET", "finsight")}/warehouse',
            's3.endpoint': os.environ['MINIO_ENDPOINT'],
            's3.access-key-id': os.environ['MINIO_ACCESS_KEY'],
            's3.secret-access-key': os.environ['MINIO_SECRET_KEY'],
        },
    )


def download_bronze(target_date: date, lookback_days: int = 90) -> pd.DataFrame:
    """Download Bronze Parquet files for a date range from MinIO."""
    s3 = get_s3_client()
    bucket = os.environ.get('S3_BUCKET', 'finsight')

    frames = []
    current = target_date - timedelta(days=lookback_days)
    while current <= target_date:
        key = f"bronze/bars/date={current}/batch.parquet"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            df = pd.read_parquet(BytesIO(resp['Body'].read()))
            frames.append(df)
        except s3.exceptions.NoSuchKey:
            pass
        except Exception as e:
            print(f"[warn] Could not read {key}: {e}")
        current += timedelta(days=1)

    if not frames:
        raise ValueError(f"No Bronze data found in the {lookback_days}-day window ending {target_date}")

    combined = pd.concat(frames, ignore_index=True)
    print(f"[spark] Loaded {len(combined)} rows from Bronze ({len(frames)} trading days)")
    return combined


def compute_indicators_spark(pdf: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """Use PySpark (local mode) to compute rolling indicators."""
    spark = (
        SparkSession.builder
        .master('local[*]')
        .appName('finsight_transform')
        .config('spark.sql.shuffle.partitions', '4')
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel('WARN')

    df = spark.createDataFrame(pdf)

    if 'date' not in df.columns:
        df = df.withColumn('date', F.to_date('timestamp'))
    df = df.withColumn('date', F.to_date(F.col('date').cast('string')))

    w = Window.partitionBy('symbol').orderBy('date')
    w20 = w.rowsBetween(-19, 0)
    w50 = w.rowsBetween(-49, 0)
    w30 = w.rowsBetween(-29, 0)
    w14 = w.rowsBetween(-13, 0)

    df = df.withColumn('sma_20', F.avg('close').over(w20))
    df = df.withColumn('sma_50', F.avg('close').over(w50))

    df = df.withColumn('prev_close', F.lag('close', 1).over(w))
    df = df.withColumn(
        'pct_change',
        F.when(
            F.col('prev_close').isNotNull() & (F.col('prev_close') != 0),
            ((F.col('close') - F.col('prev_close')) / F.col('prev_close')) * 100,
        ).otherwise(F.lit(None).cast('double')),
    )

    df = df.withColumn(
        'vwap_deviation',
        F.when(
            F.col('vwap').isNotNull() & (F.col('vwap') != 0),
            ((F.col('close') - F.col('vwap')) / F.col('vwap')) * 100,
        ).otherwise(F.lit(None).cast('double')),
    )

    df = df.withColumn('vol_mean_30', F.avg('volume').over(w30))
    df = df.withColumn('vol_std_30', F.stddev_pop('volume').over(w30))
    df = df.withColumn(
        'volume_zscore',
        F.when(
            F.col('vol_std_30').isNotNull() & (F.col('vol_std_30') != 0),
            (F.col('volume') - F.col('vol_mean_30')) / F.col('vol_std_30'),
        ).otherwise(F.lit(None).cast('double')),
    )

    df = df.withColumn('gain', F.greatest(F.col('pct_change'), F.lit(0.0)))
    df = df.withColumn('loss', F.greatest(-F.col('pct_change'), F.lit(0.0)))
    df = df.withColumn('avg_gain_14', F.avg('gain').over(w14))
    df = df.withColumn('avg_loss_14', F.avg('loss').over(w14))
    df = df.withColumn(
        'rsi_14',
        F.when(F.col('avg_loss_14') == 0, F.lit(100.0)).otherwise(
            100.0 - (100.0 / (1.0 + (F.col('avg_gain_14') / F.col('avg_loss_14'))))
        ),
    )

    df = df.withColumn('ingested_at', F.current_timestamp())

    target_str = str(target_date)
    silver = df.filter(F.col('date') == F.lit(target_str))

    result = silver.select(
        'symbol',
        'date',
        'open',
        'high',
        'low',
        'close',
        F.col('volume').cast('long').alias('volume'),
        'vwap',
        'sma_20',
        'sma_50',
        'rsi_14',
        'volume_zscore',
        'vwap_deviation',
        'pct_change',
        'ingested_at',
    ).toPandas()

    spark.stop()
    return result


def write_to_iceberg(df: pd.DataFrame, target_date: date) -> None:
    """Write the Silver DataFrame to Iceberg, replacing the target date's rows."""
    catalog = get_iceberg_catalog()

    namespace_exists = getattr(catalog, 'namespace_exists', None)
    if callable(namespace_exists):
        has_namespace = namespace_exists('silver')
    else:
        has_namespace = catalog._namespace_exists('silver')

    if not has_namespace:
        catalog.create_namespace('silver')

    table_exists = getattr(catalog, 'table_exists', None)
    if callable(table_exists):
        has_table = table_exists(SILVER_TABLE)
    else:
        try:
            catalog.load_table(SILVER_TABLE)
            has_table = True
        except Exception:
            has_table = False

    # PyIceberg requires timestamp[us]; Spark produces timestamp[ns] via toPandas()
    if 'ingested_at' in df.columns:
        df['ingested_at'] = df['ingested_at'].astype('datetime64[us]')

    new_arrow_table = pa.Table.from_pandas(df, preserve_index=False)

    if not has_table:
        table = catalog.create_table(
            identifier=SILVER_TABLE,
            schema=SILVER_SCHEMA,
            partition_spec=SILVER_PARTITION_SPEC,
        )
        table.append(new_arrow_table)
        print(f"[iceberg] Written {len(df)} rows to {SILVER_TABLE} for {target_date}")
        return

    table = catalog.load_table(SILVER_TABLE)
    existing_arrow = table.scan().to_arrow()

    if len(existing_arrow) > 0:
        existing_df = existing_arrow.to_pandas()
        existing_df = existing_df[existing_df['date'].astype(str) != str(target_date)]
        existing_arrow = pa.Table.from_pandas(existing_df, preserve_index=False)
        combined_arrow = pa.concat_tables([existing_arrow, new_arrow_table], promote=True)
    else:
        combined_arrow = new_arrow_table

    catalog.drop_table(SILVER_TABLE)
    table = catalog.create_table(
        identifier=SILVER_TABLE,
        schema=SILVER_SCHEMA,
        partition_spec=SILVER_PARTITION_SPEC,
    )
    table.append(combined_arrow)

    print(f"[iceberg] Written {len(df)} rows to {SILVER_TABLE} for {target_date}")


def run(target_date: date = None) -> None:
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    print(f"[transform] Processing {target_date}")

    bronze_df = download_bronze(target_date)
    silver_df = compute_indicators_spark(bronze_df, target_date)

    if silver_df.empty:
        print(f"[transform] No Silver rows produced for {target_date} - skipping write.")
        sys.exit(0)

    write_to_iceberg(silver_df, target_date)
    print(f"[transform] Done. {len(silver_df)} rows written to Silver.")


if __name__ == '__main__':
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(target)
